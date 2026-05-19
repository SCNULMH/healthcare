from fastapi import APIRouter

from app.core.config import get_settings
from app.services.public_data import PublicDataClient


router = APIRouter(prefix="/health", tags=["health"])


@router.get("/ready")
async def readiness() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": "검진AI 리셋코치",
        "public_data_key_configured": settings.has_public_data_key,
        "use_demo_data": settings.use_demo_data,
    }


@router.get("/public-data")
async def public_data_status() -> dict:
    settings = get_settings()
    client = PublicDataClient(settings)
    return await client.check_status()
