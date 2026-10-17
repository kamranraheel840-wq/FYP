"""Authentication helpers: hashing, policy, lockout."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
try:
    from sqlcipher3 import dbapi2 as sqlite3
except ModuleNotFoundError:
    import sqlite3
import time
from datetime import datetime, timezone

from config import LOCKOUT_SECONDS, MAX_LOGIN_ATTEMPTS, MIN_PASSWORD_LENGTH, POLICE_DB
from secure_storage import secure_connect

PBKDF2_ROUNDS = 180_000
USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")
DEFAULT_PASSWORDS = {"admin": "admin123", "officer": "officer123"}


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return base64.b64encode(salt + digest).decode("ascii")


def verify_password(password: str, encoded: str) -> bool:
    try:
        raw = base64.b64decode(encoded.encode("ascii"))
        salt, digest = raw[:16], raw[16:]
        check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
        if hmac.compare_digest(check, digest):
            return True
        # Accept hashes created with the previous iteration count.
        legacy = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
        return hmac.compare_digest(legacy, digest)
    except Exception:
        return False


def password_issues(password: str, username: str = "") -> list[str]:
    issues = []
    if len(password) < MIN_PASSWORD_LENGTH:
        issues.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if not re.search(r"[A-Za-z]", password):
        issues.append("Password must include a letter.")
    if not re.search(r"\d", password):
        issues.append("Password must include a number.")
    if username and password.lower() == username.lower():
        issues.append("Password cannot match the username.")
    if password.lower() in {"password", "admin123", "officer123", "12345678"}:
        issues.append("Choose a stronger password than the default/demo value.")
    return issues


def valid_username(username: str) -> bool:
    return bool(USERNAME_RE.fullmatch(username or ""))


def is_default_password(username: str, password: str) -> bool:
    return DEFAULT_PASSWORDS.get((username or "").lower()) == password


def auth_connect() -> sqlite3.Connection:
    conn = secure_connect(POLICE_DB, timeout=30.0)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def ensure_user_security_columns(conn: sqlite3.Connection) -> None:
    cols = {r[1] for r in conn.execute("PRAGMA table_info(app_users)").fetchall()}
    extras = {
        "failed_attempts": "INTEGER DEFAULT 0",
        "locked_until": "REAL DEFAULT 0",
        "must_change": "INTEGER DEFAULT 0",
        "last_login": "TEXT",
    }
    for col, typ in extras.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE app_users ADD COLUMN {col} {typ}")


def lock_remaining(locked_until: float | None) -> int:
    if not locked_until:
        return 0
    return max(0, int(locked_until - time.time()))


def register_failure(username: str) -> int:
    conn = auth_connect()
    try:
        ensure_user_security_columns(conn)
        row = conn.execute(
            "SELECT failed_attempts FROM app_users WHERE username=?", (username,)
        ).fetchone()
        attempts = (row[0] or 0) + 1 if row else MAX_LOGIN_ATTEMPTS
        locked = time.time() + LOCKOUT_SECONDS if attempts >= MAX_LOGIN_ATTEMPTS else 0
        if row:
            conn.execute(
                "UPDATE app_users SET failed_attempts=?, locked_until=? WHERE username=?",
                (attempts, locked, username),
            )
            conn.commit()
        # Unknown usernames are not tracked and must not reveal a lockout state.
        return lock_remaining(locked) if row else 0
    finally:
        conn.close()


def register_success(username: str) -> None:
    conn = auth_connect()
    try:
        ensure_user_security_columns(conn)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE app_users SET failed_attempts=0, locked_until=0, last_login=? WHERE username=?",
            (now, username),
        )
        conn.commit()
    finally:
        conn.close()


def account_lock_seconds(username: str) -> int:
    conn = auth_connect()
    try:
        ensure_user_security_columns(conn)
        row = conn.execute(
            "SELECT locked_until FROM app_users WHERE username=?", (username,)
        ).fetchone()
        return lock_remaining(row[0] if row else 0)
    finally:
        conn.close()
