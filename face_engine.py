import os

import cv2
import numpy as np

try:
    from config import MODELS_DIR as MODEL_DIR
except Exception:
    MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
YUNET_FILENAME = "face_detection_yunet_2023mar.onnx"
SFACE_FILENAME = "face_recognition_sface_2021dec.onnx"
YUNET_MODEL = os.path.join(MODEL_DIR, YUNET_FILENAME)
SFACE_MODEL = os.path.join(MODEL_DIR, SFACE_FILENAME)

# Public download locations, shown to the user when auto-download fails.
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SFACE_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"


def _download(url: str, dest: str, progress=None) -> None:
    """Stream a file to dest with an optional progress(received_bytes, total_bytes) callback."""
    import urllib.request
    import socket as _socket

    _socket.setdefaulttimeout(60)
    tmp = dest + ".part"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            received = 0
            with open(tmp, "wb") as out:
                while True:
                    chunk = resp.read(1 << 16)
                    if not chunk:
                        break
                    out.write(chunk)
                    received += len(chunk)
                    if progress:
                        progress(received, total)
        os.replace(tmp, dest)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


class FaceEngine:
    """YuNet face detection + SFace recognition, with model auto-download.

    Both models come from the OpenCV Zoo repository. On first use the engine
    downloads them into models/; if the download fails (offline machine), it
    raises with the manual download URLs so the user can fetch them by hand.
    """

    # Public download locations, also reachable via the class for the GUI.
    YUNET_URL = YUNET_URL
    SFACE_URL = SFACE_URL

    def __init__(
        self,
        yunet_path: str = YUNET_MODEL,
        sface_path: str = SFACE_MODEL,
    ):
        self.yunet_path = yunet_path
        self.sface_path = sface_path
        self.detector = None
        self.recognizer = None

    def available(self) -> bool:
        return (
            os.path.exists(self.yunet_path)
            and os.path.exists(self.sface_path)
            and hasattr(cv2, "FaceRecognizerSF")
        )

    def status(self) -> list:
        missing = []
        if not os.path.exists(self.yunet_path):
            missing.append(os.path.basename(self.yunet_path))
        if not os.path.exists(self.sface_path):
            missing.append(os.path.basename(self.sface_path))
        if not hasattr(cv2, "FaceRecognizerSF"):
            missing.append("OpenCV >= 4.5.4 (FaceRecognizerSF)")
        return missing

    def download_models(self, progress=None) -> list:
        """Download missing models, reporting progress(filename, recv, total).

        Returns the list of filenames downloaded. Raises a RuntimeError carrying
        the manual download URLs if a model cannot be fetched.
        """
        os.makedirs(MODEL_DIR, exist_ok=True)
        downloading = []
        if not os.path.exists(self.yunet_path):
            downloading.append((YUNET_URL, self.yunet_path))
        if not os.path.exists(self.sface_path):
            downloading.append((SFACE_URL, self.sface_path))
        done = []
        for url, dest in downloading:
            label = os.path.basename(dest)
            try:
                _download(
                    url, dest, progress=lambda recv, total, _b=label: progress(_b, recv, total) if progress else None
                )
            except Exception as e:
                raise RuntimeError(
                    f"Could not download {label} ({e}).\n"
                    f"Download it manually from:\n  {url}\n"
                    f"and place it in:\n  {MODEL_DIR}"
                ) from e
            done.append(label)
        return done

    def ensure_models(self) -> None:
        """Download missing models; raise with manual URLs on failure."""
        downloads = []
        if not os.path.exists(self.yunet_path):
            downloads.append((YUNET_URL, self.yunet_path))
        if not os.path.exists(self.sface_path):
            downloads.append((SFACE_URL, self.sface_path))
        for url, dest in downloads:
            try:
                _download(url, dest)
            except Exception as e:
                raise RuntimeError(
                    f"Could not download {os.path.basename(dest)} ({e}).\n"
                    f"Download it manually from:\n  {url}\n"
                    f"and place it in:\n  {MODEL_DIR}"
                ) from e

    def load(self):
        if self.detector is not None and self.recognizer is not None:
            return True
        if not hasattr(cv2, "FaceRecognizerSF"):
            raise RuntimeError(
                "OpenCV >= 4.5.4 is required for face recognition. "
                "Run: python -m pip install -r requirements.txt"
            )
        self.ensure_models()
        if self.detector is None:
            # score_threshold 0.6 (not 0.85) so tight/face-only crops are detected.
            self.detector = cv2.FaceDetectorYN.create(
                self.yunet_path, "", (320, 320), 0.6, 0.3, 5000
            )
        if self.recognizer is None:
            self.recognizer = cv2.FaceRecognizerSF.create(self.sface_path, "")
        return True

    def _detect_on(self, image):
        h, w = image.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(image)
        return [] if faces is None else faces.tolist()

    def detect(self, image):
        """Detect faces; retries on a mirrored copy to handle off-front poses."""
        self.load()
        faces = self._detect_on(image)
        if faces:
            return faces
        # A horizontal mirror can rescue faces the model struggles with.
        mirrored = self._detect_on(cv2.flip(image, 1))
        width = image.shape[1]
        for f in mirrored:
            f[0] = float(width) - f[0] - f[2]          # box x
            for k in (4, 6, 8, 10, 12):                 # landmark x coords
                f[k] = float(width) - f[k]
            faces.append(f)
        return faces

    def embedding_from_face(self, image, face):
        self.load()
        # YuNet returns a 15-float row: x, y, w, h, then 5 landmarks (x, y each).
        # Rebuild the cv2.Mat-like row SFace's alignCrop expects.
        face_row = np.array(face, dtype=np.float32).reshape(1, -1)
        aligned = self.recognizer.alignCrop(image, face_row)
        return self._embed(aligned)

    def embedding_from_image(self, image):
        faces = self.detect(image)
        if not faces:
            raise RuntimeError("No face detected in the image.")
        if len(faces) > 1:
            # Use the largest face for enrollment/search.
            faces.sort(key=lambda f: float(f[2]) * float(f[3]), reverse=True)
        return self.embedding_from_face(image, faces[0]), faces[0], len(faces)

    def embedding_from_path(self, path):
        image = cv2.imread(path)
        if image is None:
            raise RuntimeError("Could not read image: " + path)
        return self.embedding_from_image(image)

    @staticmethod
    def cosine_similarity(a, b):
        a = np.asarray(a, dtype=np.float32)
        b = np.asarray(b, dtype=np.float32)
        den = float(np.linalg.norm(a) * np.linalg.norm(b))
        return float(np.dot(a, b) / den) if den else 0.0

    def _embed(self, aligned):
        self.load()
        # SFace features are already L2-normalized.
        return self.recognizer.feature(aligned).reshape(-1)
