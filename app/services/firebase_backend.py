from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings


def is_enabled() -> bool:
    settings = get_settings()
    return settings.database_backend.lower() == "firebase"


def get_db():
    settings = get_settings()
    if not settings.firebase_credentials_path:
        raise RuntimeError("FIREBASE_CREDENTIALS_PATH가 필요합니다.")
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError as exc:
        raise RuntimeError("firebase-admin 패키지가 설치되어야 합니다.") from exc

    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.firebase_credentials_path)
        options = {"projectId": settings.firebase_project_id} if settings.firebase_project_id else None
        firebase_admin.initialize_app(cred, options)
    return firestore.client()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_user(user_id: str, data: dict[str, Any]) -> None:
    db = get_db()
    db.collection("users").document(user_id).set(data, merge=True)


def get_user(user_id: str) -> dict[str, Any] | None:
    snap = get_db().collection("users").document(user_id).get()
    return snap.to_dict() if snap.exists else None


def find_user_by_email(email: str) -> dict[str, Any] | None:
    docs = get_db().collection("users").where("email", "==", email.lower()).limit(1).stream()
    for doc in docs:
        data = doc.to_dict()
        data["user_id"] = doc.id
        return data
    return None


def save_medical_record(user_id: str, record: dict[str, Any]) -> dict[str, Any]:
    db = get_db()
    ref = db.collection("users").document(user_id).collection("medical_records").document()
    payload = {**record, "id": ref.id, "created_at": now_iso()}
    ref.set(payload)
    return payload


def list_medical_records(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    docs = (
        get_db()
        .collection("users")
        .document(user_id)
        .collection("medical_records")
        .order_by("created_at", direction="DESCENDING")
        .limit(limit)
        .stream()
    )
    return [doc.to_dict() | {"id": doc.id} for doc in docs]


def latest_history(user_id: str) -> dict[str, Any] | None:
    docs = (
        get_db()
        .collection("users")
        .document(user_id)
        .collection("risk_history")
        .order_by("created_at", direction="DESCENDING")
        .limit(1)
        .stream()
    )
    for doc in docs:
        return doc.to_dict()
    return None


def save_history(user_id: str, item: dict[str, Any]) -> None:
    db = get_db()
    db.collection("users").document(user_id).collection("risk_history").document().set(item)


def list_history(user_id: str, limit: int = 5) -> list[dict[str, Any]]:
    docs = (
        get_db()
        .collection("users")
        .document(user_id)
        .collection("risk_history")
        .order_by("created_at", direction="DESCENDING")
        .limit(limit)
        .stream()
    )
    return [doc.to_dict() for doc in docs]
