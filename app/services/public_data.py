from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings
from app.services.demo_data import demo_profile


def map_checkup_row_to_risk_payload(row: dict[str, Any]) -> dict:
    """Convert an NHIS checkup OpenAPI row into the webapp risk input shape."""
    demo = demo_profile()
    health = dict(demo["health"])
    lifestyle = dict(demo["lifestyle"])

    health.update(
        {
            "age": _age_from_group(row.get("연령대코드(5세단위)"), health["age"]),
            "sex": "male" if _to_int(row.get("성별"), 1) == 1 else "female",
            "height_cm": _to_float(row.get("신장(5cm단위)"), health["height_cm"]),
            "weight_kg": _to_float(row.get("체중(5kg단위)"), health["weight_kg"]),
            "waist_cm": _to_float(row.get("허리둘레"), health["waist_cm"]),
            "systolic_bp": _to_int(row.get("수축기혈압"), health["systolic_bp"]),
            "diastolic_bp": _to_int(row.get("이완기혈압"), health["diastolic_bp"]),
            "fasting_glucose": _to_int(row.get("식전혈당(공복혈당)"), health["fasting_glucose"]),
            "total_cholesterol": _to_int(row.get("총콜레스테롤"), health["total_cholesterol"]),
            "hdl": _to_int(row.get("HDL콜레스테롤"), health["hdl"]),
            "ldl": _to_int(row.get("LDL콜레스테롤"), health["ldl"]),
            "triglyceride": _to_int(row.get("트리글리세라이드"), health["triglyceride"]),
        }
    )

    smoking_code = _to_int(row.get("흡연상태"), 0)
    lifestyle["smoking"] = {1: "never", 2: "past", 3: "current"}.get(smoking_code, lifestyle["smoking"])
    lifestyle["drinking"] = "light" if _to_int(row.get("음주여부"), 0) == 1 else "none"

    return {
        "health": health,
        "lifestyle": lifestyle,
        "source": {
            "dataset": "국민건강보험공단_건강검진정보",
            "year": row.get("기준년도"),
            "note": "공공데이터 샘플 행을 MVP 입력 스키마로 변환했습니다. 지질 수치가 비어 있으면 데모 기본값을 사용합니다.",
        },
    }


class PublicDataClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def fetch_json(self, path: str, page: int = 1, per_page: int = 10) -> dict:
        if self.settings.use_demo_data:
            return _demo_public_data_response()

        if not self.settings.has_public_data_key:
            return {
                "status": "missing_key",
                "message": "PUBLIC_DATA_SERVICE_KEY 환경변수가 설정되어야 합니다.",
                "data": [_demo_public_data_row()],
            }

        url = f"{self.settings.public_data_base_url.rstrip('/')}{path}"
        params = {
            "page": page,
            "perPage": per_page,
            "returnType": "JSON",
            "serviceKey": self.settings.public_data_service_key,
        }
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            return {
                "status": "fallback_demo",
                "message": f"공공데이터 API 호출 실패로 데모 샘플을 사용합니다: {exc}",
                "data": [_demo_public_data_row()],
            }

    async def fetch_checkup_sample(self, per_page: int = 3) -> dict:
        return await self.fetch_json(self.settings.checkup_dataset_path, page=1, per_page=per_page)

    async def fetch_group_checkup_sample(self, per_page: int = 3) -> dict:
        return await self.fetch_json(self.settings.checkup_group_dataset_path, page=1, per_page=per_page)

    async def fetch_checkup_prefill(self, index: int = 0) -> dict:
        sample = await self.fetch_checkup_sample(per_page=max(index + 1, 1))
        rows = sample.get("data") or []
        if not rows:
            return {
                "status": sample.get("status", "empty"),
                "message": sample.get("message", "건강검진정보 샘플 행을 찾지 못했습니다."),
                "prefill": demo_profile(),
            }

        selected = rows[min(index, len(rows) - 1)]
        prefill = map_checkup_row_to_risk_payload(selected)
        return {
            "status": "mapped",
            "message": "건강검진정보 샘플을 입력폼에 맞게 변환했습니다.",
            "prefill": {"health": prefill["health"], "lifestyle": prefill["lifestyle"]},
            "source": prefill["source"],
        }

    async def check_status(self) -> dict:
        if self.settings.use_demo_data:
            return {
                "status": "demo",
                "message": "USE_DEMO_DATA=true 상태라 공공데이터 API 대신 데모 데이터를 사용합니다.",
            }

        if not self.settings.has_public_data_key:
            return {
                "status": "missing_key",
                "message": "PUBLIC_DATA_SERVICE_KEY 환경변수가 설정되면 공공데이터 API 연결 테스트를 실행할 수 있습니다.",
            }

        try:
            sample = await self.fetch_checkup_sample(per_page=1)
            if sample.get("status") == "fallback_demo":
                return {
                    "status": "fallback_demo",
                    "base_url": self.settings.public_data_base_url,
                    "sample_count": len(sample.get("data", [])),
                    "message": sample.get("message", "공공데이터 API 호출 실패로 데모 데이터를 사용합니다."),
                }
            return {
                "status": "reachable",
                "base_url": self.settings.public_data_base_url,
                "dataset": "국민건강보험공단_건강검진정보_20221231",
                "sample_count": sample.get("currentCount", 0),
                "total_count": sample.get("totalCount"),
                "message": "서비스 키가 설정되어 있고 건강검진정보 샘플 조회가 가능합니다.",
            }
        except httpx.HTTPStatusError as exc:
            return {
                "status": "http_error",
                "base_url": self.settings.public_data_base_url,
                "http_status": exc.response.status_code,
                "message": exc.response.text[:500],
            }
        except httpx.HTTPError as exc:
            return {
                "status": "network_error",
                "base_url": self.settings.public_data_base_url,
                "message": str(exc),
            }


def _demo_public_data_response() -> dict:
    return {
        "status": "demo",
        "currentCount": 1,
        "totalCount": 1,
        "data": [_demo_public_data_row()],
    }


def _demo_public_data_row() -> dict:
    return {
        "기준년도": "2022",
        "연령대코드(5세단위)": "9",
        "성별": "1",
        "신장(5cm단위)": "170",
        "체중(5kg단위)": "80",
        "허리둘레": "92",
        "수축기혈압": "132",
        "이완기혈압": "86",
        "식전혈당(공복혈당)": "132",
        "총콜레스테롤": "218",
        "HDL콜레스테롤": "42",
        "LDL콜레스테롤": "138",
        "트리글리세라이드": "185",
        "흡연상태": "2",
        "음주여부": "1",
    }


def _to_float(value: Any, default: float) -> float:
    try:
        if value in (None, ""):
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_int(value: Any, default: int) -> int:
    return int(round(_to_float(value, default)))


def _age_from_group(value: Any, default: int) -> int:
    code = _to_int(value, 0)
    if code <= 0:
        return default
    return min(max(code * 5 - 2, 19), 100)
