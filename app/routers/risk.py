from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.services.demo_data import demo_profile
from app.services.diagnosis import (
    HealthProfile,
    LifestyleProfile,
    create_personal_plan,
    evaluate_health_risks,
)
from app.services.model_runtime import model_performance_summary, model_status, predict_with_model, should_use_model
from app.services.history import get_history, save_analysis
from app.services.ocr_runtime import (
    OcrRuntimeError,
    demo_ocr_result,
    extract_checkup_values_from_upload,
    ocr_status,
)


router = APIRouter(prefix="/risk", tags=["risk"])


class HealthProfileIn(BaseModel):
    age: int = Field(ge=19, le=100)
    sex: Literal["male", "female"]
    height_cm: float = Field(gt=120, lt=230)
    weight_kg: float = Field(gt=30, lt=200)
    waist_cm: float | None = Field(default=None, gt=40, lt=160)
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
    client_id: str | None = Field(default=None, min_length=8, max_length=80)
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
        "model": model_status(),
        "ocr": ocr_status(get_settings()),
        "roadmap": [
            "MVP: 건강검진 수치와 걸음수 수동 입력",
            "Next: 검진 결과지 OCR 업로드",
            "Future: iOS HealthKit, Android Health Connect 사용자 동의 연동",
            "Future: 건강정보고속도로/의료 마이데이터 기반 검진 내역 연동",
        ],
    }


@router.get("/history/{client_id}")
async def read_history(client_id: str, limit: int = 5) -> dict:
    return get_history(client_id, limit=max(1, min(limit, 10)))


def _ai_explanation() -> dict:
    return {
        "title": "AI가 이렇게 판단했어요",
        "steps": [
            {
                "title": "위험도 예측",
                "description": "건강검진 수치와 생활패턴을 함께 분석해 고혈압·당뇨·이상지질혈증 위험도를 계산합니다.",
            },
            {
                "title": "위험 요인 설명",
                "description": "공복혈당, 혈압, BMI, 걸음수처럼 위험도를 높인 요인을 쉬운 말로 풀어줍니다.",
            },
            {
                "title": "개인 맞춤 개선 플랜",
                "description": "사용자의 생활패턴과 실천 제약을 반영해 하루 1~2개의 작은 행동으로 바꿉니다.",
            },
        ],
        "model_note": (
            "당뇨·고혈압은 공공데이터 기준값 라벨로 학습한 모델을 우선 사용하고, "
            "이상지질혈증과 생활습관 영향은 설명 가능한 규칙 엔진으로 보강합니다. "
            "모델 모드에서는 공복혈당·혈압 같은 검진값이 가장 크게 반영되므로, 작은 생활값 변화는 행동 영향표에서 별도로 확인합니다."
        ),
        "criteria": [
            {"name": "당뇨", "primary": "공복혈당 100 이상 주의, 126 이상 위험", "lifestyle": "단 음료 주 5회 이상, 운동 주 1회 이하, 5,000보 미만이면 가중"},
            {"name": "고혈압", "primary": "130/80 이상 주의, 140/90 이상 위험", "lifestyle": "외식 주 5회 이상, 음주 moderate 이상, 운동 부족, 5,000보 미만이면 가중"},
            {"name": "이상지질혈증", "primary": "총콜레스테롤 200 이상, LDL 130 이상, 중성지방 150 이상, HDL 낮음이면 주의", "lifestyle": "외식·야식·운동 부족·낮은 걸음수에 가중"},
            {"name": "BMI/허리둘레", "primary": "BMI 25 이상 과체중, 30 이상 비만. 허리둘레 남 90cm/여 85cm 이상 복부비만", "lifestyle": "체중 자체보다 식사·활동 기록 개선을 우선 권장"},
        ],
    }


def _input_notes(health: HealthProfile) -> list[str]:
    notes = []
    if health.waist_cm is None:
        notes.append(
            "허리둘레가 입력되지 않아 복부비만 직접 판정은 제외하고 BMI, 혈압, 혈당, 지질 수치와 생활패턴 중심으로 분석했습니다."
        )
    return notes


def _reliability_summary(
    health: HealthProfile,
    risk_dicts: list[dict],
    engine: dict,
) -> dict:
    performance = model_performance_summary()
    optional_missing = 1 if health.waist_cm is None else 0
    required_count = 23
    completeness = round(((required_count - optional_missing) / required_count) * 100)
    cards = []
    for risk in risk_dicts:
        perf = performance["targets"].get(risk["key"], {})
        avg = perf.get("training_positive_rate")
        diff = None if avg is None else round(risk["probability"] - avg, 1)
        cards.append(
            {
                "key": risk["key"],
                "label": risk["label"],
                "user_probability": risk["probability"],
                "training_positive_rate": avg,
                "difference_from_training_rate": diff,
                "model_status": perf.get("status", "rule"),
                "roc_auc": perf.get("roc_auc"),
                "precision": perf.get("precision"),
                "recall": perf.get("recall"),
                "rows": perf.get("rows", 0),
                "note": perf.get("note"),
            }
        )
    return {
        "input_completeness": completeness,
        "engine_mode": engine.get("mode", "rule"),
        "model_status": performance["status"],
        "cards": cards,
        "caution": performance["caution"],
    }


@router.post("/predict")
async def predict_risk(payload: RiskRequest) -> dict:
    health = HealthProfile(**payload.health.model_dump())
    lifestyle = LifestyleProfile(**payload.lifestyle.model_dump())
    risks = evaluate_health_risks(health, lifestyle)
    engine = {
        "mode": "rule",
        "status": "used",
        "message": "설명 가능한 규칙 기반 AI 엔진을 사용했습니다.",
    }
    if should_use_model():
        try:
            risks, engine = predict_with_model(health, lifestyle, risks)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    plan = create_personal_plan(health, lifestyle, risks)
    bmi = round(health.bmi, 1)
    risk_dicts = [risk.to_dict() for risk in risks]
    comparison = save_analysis(
        client_id=payload.client_id,
        bmi=bmi,
        risks=risk_dicts,
        plan=plan,
        health=payload.health.model_dump(),
        lifestyle=payload.lifestyle.model_dump(),
    )
    return {
        "disclaimer": "예측 결과는 진단이 아니며, 정확한 판단과 치료는 의료진 상담이 필요합니다.",
        "bmi": bmi,
        "risks": risk_dicts,
        "plan": plan,
        "ai_explanation": _ai_explanation(),
        "engine": engine,
        "input_notes": _input_notes(health),
        "comparison": comparison,
        "reliability": _reliability_summary(health, risk_dicts, engine),
    }


@router.post("/ocr/demo")
async def ocr_demo() -> dict:
    return demo_ocr_result()


@router.post("/ocr/extract")
async def extract_checkup_values(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> dict:
    try:
        return await extract_checkup_values_from_upload(file, settings)
    except OcrRuntimeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
