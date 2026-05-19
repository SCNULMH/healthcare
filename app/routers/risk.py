from typing import Literal

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field

from app.services.demo_data import demo_profile
from app.services.diagnosis import (
    HealthProfile,
    LifestyleProfile,
    create_personal_plan,
    evaluate_health_risks,
)


router = APIRouter(prefix="/risk", tags=["risk"])


class HealthProfileIn(BaseModel):
    age: int = Field(ge=19, le=100)
    sex: Literal["male", "female"]
    height_cm: float = Field(gt=120, lt=230)
    weight_kg: float = Field(gt=30, lt=200)
    waist_cm: float = Field(gt=40, lt=160)
    systolic_bp: int = Field(ge=70, le=240)
    diastolic_bp: int = Field(ge=40, le=160)
    fasting_glucose: int = Field(ge=50, le=400)
    total_cholesterol: int = Field(ge=80, le=400)
    hdl: int = Field(ge=10, le=150)
    ldl: int = Field(ge=30, le=300)
    triglyceride: int = Field(ge=30, le=800)


class LifestyleProfileIn(BaseModel):
    breakfast: Literal["regular", "sometimes", "rarely"]
    sugary_drinks_per_week: int = Field(ge=0, le=30)
    late_meals_per_week: int = Field(ge=0, le=14)
    exercise_per_week: int = Field(ge=0, le=14)
    eating_out_per_week: int = Field(ge=0, le=21)
    sleep_hours: float = Field(ge=3, le=12)
    avg_steps: int = Field(ge=0, le=50000)
    smoking: Literal["never", "past", "current"]
    drinking: Literal["none", "light", "moderate", "heavy"]
    available_minutes_per_day: int = Field(ge=5, le=120)
    can_prepare_meals: bool


class RiskRequest(BaseModel):
    health: HealthProfileIn
    lifestyle: LifestyleProfileIn


@router.get("/demo")
async def get_demo() -> dict:
    return demo_profile()


@router.get("/metadata")
async def get_metadata() -> dict:
    return {
        "product": "검진AI 리셋코치",
        "disclaimer": "이 서비스는 의료 진단이 아니라 건강검진 기반 예방관리 참고 정보입니다.",
        "targets": ["고혈압 위험군", "당뇨 위험군", "이상지질혈증 위험군"],
        "principles": [
            "하루 1~2개의 작은 행동만 제안합니다.",
            "극단적인 식단과 과도한 운동을 권하지 않습니다.",
            "복합 위험은 가장 큰 위험 요인 1~2개부터 개선합니다.",
        ],
        "roadmap": [
            "MVP: 건강검진 수치와 걸음수 수동 입력",
            "Next: 검진 결과지 OCR 업로드",
            "Future: iOS HealthKit, Android Health Connect 사용자 동의 연동",
            "Future: 건강정보고속도로/의료 마이데이터 기반 검진 내역 연동",
        ],
    }


@router.post("/predict")
async def predict_risk(payload: RiskRequest) -> dict:
    health = HealthProfile(**payload.health.model_dump())
    lifestyle = LifestyleProfile(**payload.lifestyle.model_dump())
    risks = evaluate_health_risks(health, lifestyle)
    plan = create_personal_plan(health, lifestyle, risks)
    return {
        "disclaimer": "예측 결과는 진단이 아니며, 정확한 판단과 치료는 의료진 상담이 필요합니다.",
        "bmi": round(health.bmi, 1),
        "risks": [risk.to_dict() for risk in risks],
        "plan": plan,
    }


@router.post("/ocr/demo")
async def ocr_demo() -> dict:
    return {
        "message": "OCR 데모: 검진 결과지에서 주요 수치를 추출한 것처럼 입력폼을 채웠습니다. 실제 OCR 엔진은 다음 단계에서 연결합니다.",
        "prefill": demo_profile(),
    }


@router.post("/ocr/extract")
async def extract_checkup_values(file: UploadFile = File(...)) -> dict:
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "status": "demo_extracted",
        "message": "업로드한 검진 결과지에서 주요 검진 수치를 추출한 데모 결과입니다. 실제 OCR 엔진 연결 전까지는 샘플 값을 반환합니다.",
        "prefill": demo_profile(),
        "extracted_fields": [
            "수축기혈압",
            "이완기혈압",
            "공복혈당",
            "총콜레스테롤",
            "HDL",
            "LDL",
            "중성지방",
        ],
    }
