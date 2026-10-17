# Face AI Models

Two ONNX models power face recognition. They are downloaded **automatically on first use** into this folder:

- `face_detection_yunet_2023mar.onnx` — YuNet face detector (~230 KB)
- `face_recognition_sface_2021dec.onnx` — SFace face embedding model (~39 MB)

If your machine is offline, download them manually and place them here:

1. YuNet (face detection):
   https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx

2. SFace (face recognition):
   https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx

The application uses OpenCV's YuNet for detection and `cv2.FaceRecognizerSF` (SFace) for embeddings, then compares embeddings with cosine similarity.