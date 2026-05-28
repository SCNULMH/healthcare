from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services import account_store, firebase_backend


router = APIRouter(prefix="/account", tags=["account"])


class ProfilePayload(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    sex: str | None = Field(default=None, max_length=20)
    age: int | None = Field(default=None, ge=0, le=120)
    height_cm: float | None = Field(default=None, gt=0, lt=250)
    weight_kg: float | None = Field(default=None, gt=0, lt=250)
    waist_cm: float | None = Field(default=None, gt=0, lt=200)
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=160)
    conditions: str | None = Field(default=None, max_length=500)
    medications: str | None = Field(default=None, max_length=500)
    allergies: str | None = Field(default=None, max_length=500)
    medical_note: str | None = Field(default=None, max_length=1000)
    email: str | None = Field(default=None, max_length=160)


class RegisterPayload(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=8, max_length=120)
    profile: ProfilePayload = Field(default_factory=ProfilePayload)


class LoginPayload(BaseModel):
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=8, max_length=120)


class MedicalRecordPayload(BaseModel):
    record_date: str | None = Field(default=None, max_length=30)
    institution: str | None = Field(default=None, max_length=100)
    diagnosis: str | None = Field(default=None, max_length=200)
    medications: str | None = Field(default=None, max_length=500)
    memo: str | None = Field(default=None, max_length=1000)


@router.get("/status")
async def account_status() -> dict:
    settings = get_settings()
    return {
        "database_backend": settings.database_backend,
        "firebase_requested": firebase_backend.is_requested(),
        "firebase_enabled": firebase_backend.is_enabled(),
        "firebase_project_id": settings.firebase_project_id,
        "firebase_web_app_id": settings.firebase_web_app_id,
        "credential_configured": firebase_backend.has_credentials(),
        "credential_source": "json_env" if settings.firebase_credentials_json else "file_path" if settings.firebase_credentials_path else "missing",
        "fallback_backend": "sqlite" if firebase_backend.is_requested() and not firebase_backend.has_credentials() else None,
    }


@router.post("/register")
async def register(payload: RegisterPayload) -> dict:
    try:
        user = account_store.create_user(payload.email, payload.password, payload.profile.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "created", "user": account_store.with_session_token(user)}


@router.post("/login")
async def login(payload: LoginPayload) -> dict:
    try:
        user = account_store.login(payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {"status": "ok", "user": account_store.with_session_token(user)}


@router.get("/profile/{user_id}")
async def get_profile(user_id: str) -> dict:
    user = account_store.get_profile(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    return {"status": "ok", "user": user}


@router.put("/profile/{user_id}")
async def update_profile(user_id: str, payload: ProfilePayload) -> dict:
    try:
        user = account_store.update_profile(user_id, payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", "user": user}


@router.post("/medical-records/{user_id}")
async def add_medical_record(user_id: str, payload: MedicalRecordPayload) -> dict:
    try:
        record = account_store.add_medical_record(user_id, payload.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "created", "record": record}


@router.get("/medical-records/{user_id}")
async def get_medical_records(user_id: str, limit: int = 10) -> dict:
    return {"status": "ok", "records": account_store.list_medical_records(user_id, limit=max(1, min(limit, 20)))}
