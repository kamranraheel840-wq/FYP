"""Application paths and constants."""
from __future__ import annotations

import os
import shutil
import sys

from secure_storage import secure_connect, secure_permissions

APP_NAME = "Criminal Record Management System"
APP_VERSION = "3.1"
ORGANIZATION = "Balochistan Police"

IS_FROZEN = getattr(sys, "frozen", False)
BASE_DIR = (
    os.path.dirname(os.path.abspath(sys.executable))
    if IS_FROZEN else os.path.dirname(os.path.abspath(__file__))
)
RESOURCE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
if IS_FROZEN:
    APP_DATA_DIR = os.path.join(
        os.environ.get(
            "LOCALAPPDATA",
            os.path.join(os.path.expanduser("~"), "AppData", "Local"),
        ),
        "CriminalRecordManagementSystem",
    )
else:
    APP_DATA_DIR = BASE_DIR

DATA_DIR = os.path.join(APP_DATA_DIR, "data")
MEDIA_DIR = os.path.join(APP_DATA_DIR, "media")
MODELS_DIR = os.path.join(APP_DATA_DIR, "models")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

CRIMINALS_DB = os.path.join(DATA_DIR, "criminals.db")
POLICE_DB = os.path.join(DATA_DIR, "police.db")

IDLE_TIMEOUT_MS = 20 * 60 * 1000
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 120
MIN_PASSWORD_LENGTH = 8


def ensure_directories() -> None:
    for path in (DATA_DIR, MEDIA_DIR, MODELS_DIR, BACKUP_DIR):
        os.makedirs(path, exist_ok=True)
    packaged_models = os.path.join(RESOURCE_DIR, "models")
    for filename in (
        "face_detection_yunet_2023mar.onnx",
        "face_recognition_sface_2021dec.onnx",
    ):
        source = os.path.join(packaged_models, filename)
        destination = os.path.join(MODELS_DIR, filename)
        if os.path.isfile(source) and not os.path.exists(destination):
            shutil.copy2(source, destination)
    for path in (DATA_DIR, MEDIA_DIR, BACKUP_DIR):
        secure_permissions(path)
    _migrate_legacy_db("criminals.db", CRIMINALS_DB)
    _migrate_legacy_db("police.db", POLICE_DB)


def _migrate_legacy_db(filename: str, dest: str) -> None:
    old = os.path.join(BASE_DIR, filename)
    if os.path.isfile(old) and not os.path.isfile(dest):
        source = secure_connect(old)
        target = secure_connect(dest)
        try:
            source.backup(target)
            target.commit()
        finally:
            target.close()
            source.close()


def is_under_dir(path: str, directory: str) -> bool:
    real = os.path.abspath(path)
    root = os.path.abspath(directory)
    try:
        return os.path.commonpath([real, root]) == root
    except ValueError:
        return False
