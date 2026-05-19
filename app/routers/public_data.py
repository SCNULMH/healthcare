from fastapi import APIRouter, Query

from app.core.config import get_settings
from app.services.public_data import PublicDataClient


router = APIRouter(prefix="/data", tags=["public-data"])


@router.get("/checkup/sample")
async def checkup_sample(per_page: int = Query(default=3, ge=1, le=100)) -> dict:
    client = PublicDataClient(get_settings())
    return await client.fetch_checkup_sample(per_page=per_page)


@router.get("/checkup/prefill")
async def checkup_prefill(index: int = Query(default=0, ge=0, le=99)) -> dict:
    client = PublicDataClient(get_settings())
    return await client.fetch_checkup_prefill(index=index)


@router.get("/group-checkup/sample")
async def group_checkup_sample(per_page: int = Query(default=3, ge=1, le=100)) -> dict:
    client = PublicDataClient(get_settings())
    return await client.fetch_group_checkup_sample(per_page=per_page)
