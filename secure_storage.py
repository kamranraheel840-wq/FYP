"""Per-user key management and encrypted SQLite/photo storage."""
from __future__ import annotations

import ctypes
import os
import secrets
import subprocess
import tempfile
from contextlib import contextmanager
from ctypes import wintypes
from typing import Generator

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
try:
    from sqlcipher3 import dbapi2 as sqlite3
    SQLCIPHER_AVAILABLE = True
except ModuleNotFoundError:
    import sqlite3
    SQLCIPHER_AVAILABLE = False

_PHOTO_MAGIC = b"CRMENC1"
_MASTER_KEY: bytes | None = None
_SECURED_PATHS: set[str] = set()


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def secure_permissions(path: str, force: bool = False) -> None:
    """Restrict sensitive files/directories to the current OS user."""
    path = os.path.abspath(path)
    if not os.path.exists(path):
        return
    normalized_path = os.path.normcase(path)
    if not force and normalized_path in _SECURED_PATHS:
        return
    if os.name == "nt":
        user = subprocess.run(
            ["whoami"], check=True, capture_output=True, text=True
        ).stdout.strip()
        is_directory = os.path.isdir(path)
        subprocess.run(
            ["icacls", path, "/reset", "/T"] if is_directory
            else ["icacls", path, "/reset"],
            check=True, capture_output=True, text=True,
        )
        targets = [path]
        if is_directory:
            for root, dirs, files in os.walk(path):
                targets.extend(os.path.join(root, name) for name in dirs)
                targets.extend(os.path.join(root, name) for name in files)
        for target in targets:
            access = f"{user}:(OI)(CI)F" if os.path.isdir(target) else f"{user}:F"
            subprocess.run(
                ["icacls", target, "/inheritance:r", "/grant:r", access],
                check=True, capture_output=True, text=True,
            )
        _SECURED_PATHS.add(normalized_path)
        return

    if os.path.isdir(path):
        os.chmod(path, 0o700)
        for root, dirs, files in os.walk(path):
            for name in dirs:
                os.chmod(os.path.join(root, name), 0o700)
            for name in files:
                os.chmod(os.path.join(root, name), 0o600)
    else:
        os.chmod(path, 0o600)
    _SECURED_PATHS.add(normalized_path)


@contextmanager
def secure_output_path(destination: str) -> Generator[str, None, None]:
    """Yield a restricted same-directory temp path and atomically publish it."""
    destination = os.path.abspath(destination)
    directory = os.path.dirname(destination)
    suffix = os.path.splitext(destination)[1] or ".tmp"
    fd, temp_path = tempfile.mkstemp(prefix="crm-export-", suffix=suffix, dir=directory)
    os.close(fd)
    try:
        secure_permissions(temp_path, force=True)
        yield temp_path
        secure_permissions(temp_path, force=True)
        os.replace(temp_path, destination)
        secure_permissions(destination, force=True)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _dpapi(data: bytes, protect: bool) -> bytes:
    source_buffer = ctypes.create_string_buffer(data)
    source = _DataBlob(len(data), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte)))
    result = _DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_DataBlob), wintypes.LPCWSTR, ctypes.POINTER(_DataBlob),
        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_DataBlob), ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(_DataBlob), ctypes.c_void_p, ctypes.c_void_p,
        wintypes.DWORD, ctypes.POINTER(_DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    if protect:
        ok = crypt32.CryptProtectData(
            ctypes.byref(source), None, None, None, None, 0x1, ctypes.byref(result)
        )
    else:
        ok = crypt32.CryptUnprotectData(
            ctypes.byref(source), None, None, None, None, 0x1, ctypes.byref(result)
        )
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel32.LocalFree(result.pbData)


def _key_path() -> str:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("Windows per-user application data directory is unavailable.")
    directory = os.path.join(local_app_data, "CriminalRecordManagementSystem")
    os.makedirs(directory, exist_ok=True)
    secure_permissions(directory)
    return os.path.join(directory, "database.key")


def _get_master_key() -> bytes:
    global _MASTER_KEY
    if _MASTER_KEY is not None:
        return _MASTER_KEY

    path = _key_path() if os.name == "nt" else os.path.join(
        os.path.expanduser("~"), ".criminal-record-management-system", "database.key"
    )
    if os.path.exists(path):
        with open(path, "rb") as key_file:
            protected = key_file.read()
        key = _dpapi(protected, False) if os.name == "nt" else protected
        if len(key) != 32:
            raise RuntimeError("The protected database key is invalid.")
    else:
        key = secrets.token_bytes(32)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        protected = _dpapi(key, True) if os.name == "nt" else key
        fd, temp_path = tempfile.mkstemp(prefix="database-key-", dir=os.path.dirname(path))
        try:
            with os.fdopen(fd, "wb") as key_file:
                key_file.write(protected)
                key_file.flush()
                os.fsync(key_file.fileno())
            secure_permissions(temp_path, force=True)
            try:
                if os.name == "nt":
                    os.rename(temp_path, path)
                else:
                    os.link(temp_path, path)
            except FileExistsError:
                with open(path, "rb") as key_file:
                    protected = key_file.read()
                key = _dpapi(protected, False) if os.name == "nt" else protected
                if len(key) != 32:
                    raise RuntimeError("The protected database key is invalid.")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    if not os.path.isfile(path):
        raise RuntimeError("Could not persist the protected database key.")
    secure_permissions(path, force=True)
    _MASTER_KEY = key
    return key


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _table_row_counts(conn: sqlite3.Connection) -> dict[str, int]:
    table_names = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    counts = {}
    for (name,) in table_names:
        quoted_name = '"' + name.replace('"', '""') + '"'
        counts[name] = conn.execute(f"SELECT count(*) FROM {quoted_name}").fetchone()[0]
    return counts


def _open_encrypted(path: str, key: bytes, timeout: float) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=timeout)
    if not SQLCIPHER_AVAILABLE:
        conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
        return conn
    try:
        conn.execute(f'PRAGMA key = "x\'{key.hex()}\'"')
        conn.execute("PRAGMA cipher_memory_security = ON")
        conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
        return conn
    except Exception:
        conn.close()
        raise


def _migrate_plaintext_database(path: str, key: bytes, timeout: float) -> None:
    source = sqlite3.connect(path, timeout=timeout)
    snapshot = sqlite3.connect(":memory:")
    fd, encrypted_path = tempfile.mkstemp(prefix="encrypted-db-", suffix=".tmp",
                                           dir=os.path.dirname(os.path.abspath(path)))
    os.close(fd)
    os.remove(encrypted_path)
    try:
        try:
            source.backup(snapshot)
            source.close()
            expected_counts = _table_row_counts(snapshot)
            snapshot.execute(
                f"ATTACH DATABASE {_sql_literal(encrypted_path)} AS encrypted "
                f'KEY "x\'{key.hex()}\'"'
            )
            snapshot.execute("SELECT sqlcipher_export('encrypted')")
            snapshot.execute("DETACH DATABASE encrypted")
            snapshot.commit()
        except Exception:
            source.close()
            raise
        finally:
            snapshot.close()

        validation = _open_encrypted(encrypted_path, key, timeout)
        try:
            result = validation.execute("PRAGMA integrity_check").fetchone()
            actual_counts = _table_row_counts(validation)
        finally:
            validation.close()
        if not result or result[0] != "ok":
            raise RuntimeError(f"Encrypted database validation failed for {path}.")
        if actual_counts != expected_counts:
            raise RuntimeError(f"Encrypted database record counts do not match for {path}.")
        os.replace(encrypted_path, path)
        secure_permissions(path, force=True)
    finally:
        if os.path.exists(encrypted_path):
            os.remove(encrypted_path)


def secure_connect(path: str, timeout: float = 30.0) -> sqlite3.Connection:
    """Open an encrypted database, migrating a valid legacy SQLite file once.

    When SQLCipher is unavailable (for example in a portable local environment),
    the app falls back to standard SQLite so the desktop workflow remains usable.
    """
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    if os.path.exists(path) and not os.access(path, os.W_OK):
        os.chmod(path, 0o666)
    if not SQLCIPHER_AVAILABLE:
        conn = sqlite3.connect(path, timeout=timeout)
        conn.execute("PRAGMA foreign_keys=ON")
        secure_permissions(path)
        return conn

    key = _get_master_key()
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        conn = _open_encrypted(path, key, timeout)
        secure_permissions(path)
        _protect_legacy_database(path, key, timeout)
        return conn

    try:
        conn = _open_encrypted(path, key, timeout)
    except sqlite3.DatabaseError as encrypted_error:
        try:
            plain = sqlite3.connect(path, timeout=timeout)
            plain.execute("SELECT count(*) FROM sqlite_master").fetchone()
            plain.close()
        except sqlite3.DatabaseError:
            raise RuntimeError(
                f"Cannot open encrypted database {path}; its per-user key may be unavailable "
                "or the file may be damaged."
            ) from encrypted_error
        _migrate_plaintext_database(path, key, timeout)
        conn = _open_encrypted(path, key, timeout)
    _protect_legacy_database(path, key, timeout)
    return conn


def _protect_legacy_database(path: str, key: bytes, timeout: float) -> None:
    path = os.path.abspath(path)
    data_dir = os.path.dirname(path)
    if os.path.basename(data_dir).casefold() != "data":
        return
    if os.path.basename(path).casefold() not in {"criminals.db", "police.db"}:
        return
    legacy_path = os.path.join(os.path.dirname(data_dir), os.path.basename(path))
    if not os.path.isfile(legacy_path):
        return
    try:
        legacy = _open_encrypted(legacy_path, key, timeout)
    except sqlite3.DatabaseError as encrypted_error:
        try:
            plain = sqlite3.connect(legacy_path, timeout=timeout)
            plain.execute("SELECT count(*) FROM sqlite_master").fetchone()
            plain.close()
        except sqlite3.DatabaseError:
            raise RuntimeError(
                f"Cannot secure legacy database {legacy_path}; it may be damaged."
            ) from encrypted_error
        _migrate_plaintext_database(legacy_path, key, timeout)
    else:
        legacy.close()
    secure_permissions(legacy_path)


def _photo_key() -> bytes:
    import hashlib
    import hmac

    return hmac.new(_get_master_key(), b"criminal-record-photo-v1", hashlib.sha256).digest()


def encrypt_photo_data(data: bytes) -> bytes:
    nonce = secrets.token_bytes(12)
    return _PHOTO_MAGIC + nonce + AESGCM(_photo_key()).encrypt(nonce, data, _PHOTO_MAGIC)


def decrypt_photo_data(data: bytes) -> bytes:
    if not data.startswith(_PHOTO_MAGIC):
        return data
    nonce_start = len(_PHOTO_MAGIC)
    nonce = data[nonce_start:nonce_start + 12]
    if len(nonce) != 12:
        raise ValueError("Encrypted photo data is incomplete.")
    return AESGCM(_photo_key()).decrypt(nonce, data[nonce_start + 12:], _PHOTO_MAGIC)


def protect_photo_file(path: str) -> None:
    with open(path, "rb") as photo_file:
        data = photo_file.read()
    if data.startswith(_PHOTO_MAGIC):
        return
    encrypted = encrypt_photo_data(data)
    fd, temp_path = tempfile.mkstemp(prefix="photo-", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "wb") as photo_file:
            photo_file.write(encrypted)
            photo_file.flush()
            os.fsync(photo_file.fileno())
        secure_permissions(temp_path, force=True)
        os.replace(temp_path, path)
        secure_permissions(path, force=True)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
