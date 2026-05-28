from __future__ import annotations

import hashlib
import hmac
import base64
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services import firebase_backend


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_id(email: str) -> str:
    return hashlib.sha256(email.lower().encode("utf-8")).hexdigest()[:32]


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000)
    return salt, digest.hex()


def _verify_password(password: str, salt: str, password_hash: str) -> bool:
    _, candidate = _hash_password(password, salt)
    return hmac.compare_digest(candidate, password_hash)


def create_session_token(user_id: str) -> str:
    settings = get_settings()
    issued_at = int(datetime.now(timezone.utc).timestamp())
    payload = {"user_id": user_id, "iat": issued_at}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")
    signature = hmac.new(settings.session_secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def verify_session_token(user_id: str, token: str | None) -> bool:
    if not token or "." not in token:
        return False
    settings = get_settings()
    encoded, signature = token.rsplit(".", 1)
    expected = hmac.new(settings.session_secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False
    try:
        payload = json.loads(base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return False
    if payload.get("user_id") != user_id:
        return False
    issued_at = int(payload.get("iat") or 0)
    now = int(datetime.now(timezone.utc).timestamp())
    return issued_at > 0 and now - issued_at <= settings.session_ttl_seconds


def with_session_token(user: dict[str, Any]) -> dict[str, Any]:
    return {**user, "session_token": create_session_token(user["user_id"])}


def _connect() -> sqlite3.Connection:
    settings = get_settings()
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            profile_payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS medical_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            record_date TEXT,
            institution TEXT,
            diagnosis TEXT,
            memo TEXT,
            medications TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    return conn


def create_user(email: str, password: str, profile: dict[str, Any]) -> dict[str, Any]:
    normalized = email.lower().strip()
    user_id = _user_id(normalized)
    salt, password_hash = _hash_password(password)
    payload = {
        "user_id": user_id,
        "email": normalized,
        "password_salt": salt,
        "password_hash": password_hash,
        "profile": profile,
        "created_at": _now(),
        "updated_at": _now(),
    }
    if firebase_backend.is_enabled():
        existing = firebase_backend.find_user_by_email(normalized)
        if existing:
            raise ValueError("이미 가입된 이메일입니다.")
        firebase_backend.save_user(user_id, payload)
        return _public_user(payload)

    conn = _connect()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO users (
                    user_id, email, password_salt, password_hash,
                    profile_payload, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    normalized,
                    salt,
                    password_hash,
                    json.dumps(profile, ensure_ascii=False),
                    payload["created_at"],
                    payload["updated_at"],
                ),
            )
    except sqlite3.IntegrityError as exc:
        raise ValueError("이미 가입된 이메일입니다.") from exc
    return _public_user(payload)


def login(email: str, password: str) -> dict[str, Any]:
    normalized = email.lower().strip()
    if firebase_backend.is_enabled():
        user = firebase_backend.find_user_by_email(normalized)
        if not user or not _verify_password(password, user["password_salt"], user["password_hash"]):
            raise ValueError("이메일 또는 비밀번호가 맞지 않습니다.")
        return _public_user(user)

    row = _connect().execute("SELECT * FROM users WHERE email = ?", (normalized,)).fetchone()
    if not row or not _verify_password(password, row["password_salt"], row["password_hash"]):
        raise ValueError("이메일 또는 비밀번호가 맞지 않습니다.")
    return {
        "user_id": row["user_id"],
        "email": row["email"],
        "profile": json.loads(row["profile_payload"]),
    }


def get_profile(user_id: str) -> dict[str, Any] | None:
    if firebase_backend.is_enabled():
        user = firebase_backend.get_user(user_id)
        return _public_user(user) if user else None

    row = _connect().execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return None
    return {"user_id": row["user_id"], "email": row["email"], "profile": json.loads(row["profile_payload"])}


def update_profile(user_id: str, profile: dict[str, Any]) -> dict[str, Any]:
    user = get_profile(user_id)
    if not user and firebase_backend.is_enabled() and profile.get("email"):
        user = {"user_id": user_id, "email": profile["email"], "profile": {}}
        firebase_backend.save_user(user_id, {"user_id": user_id, "email": profile["email"], "profile": {}, "updated_at": _now()})
    if not user:
        raise ValueError("사용자를 찾을 수 없습니다.")
    merged = {**user.get("profile", {}), **_clean_profile(profile)}
    if firebase_backend.is_enabled():
        firebase_backend.save_user(user_id, {"profile": merged, "updated_at": _now()})
        return {"user_id": user_id, "email": user["email"], "profile": merged}

    with _connect() as conn:
        conn.execute(
            "UPDATE users SET profile_payload = ?, updated_at = ? WHERE user_id = ?",
            (json.dumps(merged, ensure_ascii=False), _now(), user_id),
        )
    return {"user_id": user_id, "email": user["email"], "profile": merged}


def add_medical_record(user_id: str, record: dict[str, Any]) -> dict[str, Any]:
    if not get_profile(user_id):
        raise ValueError("사용자를 찾을 수 없습니다.")
    if firebase_backend.is_enabled():
        return firebase_backend.save_medical_record(user_id, record)

    conn = _connect()
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO medical_records (
                user_id, record_date, institution, diagnosis, memo, medications, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                record.get("record_date"),
                record.get("institution"),
                record.get("diagnosis"),
                record.get("memo"),
                record.get("medications"),
                _now(),
            ),
        )
    return {"id": str(cursor.lastrowid), "user_id": user_id, **record}


def list_medical_records(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    if firebase_backend.is_enabled():
        return firebase_backend.list_medical_records(user_id, limit)
    rows = _connect().execute(
        """
        SELECT id, record_date, institution, diagnosis, memo, medications, created_at
        FROM medical_records
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    return [dict(row) | {"id": str(row["id"])} for row in rows]


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "profile": _clean_profile(user.get("profile", {})),
    }


def _clean_profile(profile: dict[str, Any]) -> dict[str, Any]:
    cleaned = {key: value for key, value in profile.items() if value not in {None, ""}}
    if "medical_note" not in cleaned:
        notes = []
        for key in ("conditions", "medications", "allergies"):
            value = cleaned.get(key)
            if value and value not in notes:
                notes.append(value)
        if notes:
            cleaned["medical_note"] = " / ".join(notes)
    elif isinstance(cleaned["medical_note"], str):
        cleaned["medical_note"] = _dedupe_note(cleaned["medical_note"])
    for key in ("conditions", "medications", "allergies"):
        cleaned.pop(key, None)
    cleaned.pop("email", None)
    return cleaned


def _dedupe_note(value: str) -> str:
    parts = [part.strip() for part in value.split("/") if part.strip()]
    return " / ".join(dict.fromkeys(parts))
