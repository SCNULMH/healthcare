from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.core.config import get_settings
from app.services.diagnosis import HealthProfile, LifestyleProfile, RiskResult


MODEL_TARGETS = {
    "diabetes_risk": ("diabetes", "당뇨 위험군", "당뇨"),
    "hypertension_risk": ("hypertension", "고혈압 위험군", "고혈압"),
    "dyslipidemia_risk": ("dyslipidemia", "이상지질혈증 위험군", "이상지질혈증"),
}


@lru_cache
def load_model_bundle() -> dict[str, Any]:
    settings = get_settings()
    path = Path(settings.risk_model_path)
    if not path.exists():
        return {
            "status": "missing",
            "path": str(path),
            "message": "학습 모델 파일을 찾지 못해 규칙 기반 엔진을 사용합니다.",
            "features": [],
            "models": {},
            "reports": {},
        }

    try:
        bundle = joblib.load(path)
    except Exception as exc:
        return {
            "status": "load_error",
            "path": str(path),
            "message": f"학습 모델 로드 실패: {exc}",
            "features": [],
            "models": {},
            "reports": {},
        }

    return {
        "status": "loaded",
        "path": str(path),
        "message": "학습 모델 파일을 로드했습니다.",
        "features": bundle.get("features", []),
        "models": bundle.get("models", {}),
        "reports": bundle.get("reports", {}),
    }


def model_status() -> dict[str, Any]:
    settings = get_settings()
    bundle = load_model_bundle()
    return {
        "mode": settings.risk_model_mode,
        "status": bundle["status"],
        "path": bundle["path"],
        "available_targets": sorted(bundle["models"].keys()),
        "message": bundle["message"],
    }


def should_use_model() -> bool:
    settings = get_settings()
    mode = settings.risk_model_mode.lower()
    if mode in {"rule", "rules", "demo"}:
        return False
    if mode in {"model", "trained"}:
        return True
    return load_model_bundle()["status"] == "loaded"


def predict_with_model(
    health: HealthProfile,
    lifestyle: LifestyleProfile,
    rule_risks: list[RiskResult],
) -> tuple[list[RiskResult], dict[str, Any]]:
    settings = get_settings()
    bundle = load_model_bundle()
    if settings.risk_model_mode.lower() in {"model", "trained"} and bundle["status"] != "loaded":
        raise RuntimeError(bundle["message"])
    if bundle["status"] != "loaded":
        return rule_risks, model_status()

    row = _feature_row(health, lifestyle)
    features = bundle["features"]
    frame = pd.DataFrame([row], columns=features)
    by_key = {risk.key: risk for risk in rule_risks}
    merged: list[RiskResult] = []

    for target, (key, label, disease) in MODEL_TARGETS.items():
        model = bundle["models"].get(target)
        if model is None:
            merged.append(by_key[key])
            continue

        probability = int(round(float(model.predict_proba(frame)[0, 1]) * 100))
        probability = max(1, min(probability, 95))
        rule_risk = by_key[key]
        merged.append(
            RiskResult(
                key=key,
                label=label,
                level=_level(probability),
                probability=probability,
                reasons=[
                    f"학습 모델이 {disease} 검진 기준 위험군 가능성을 {probability}%로 분류했습니다.",
                    *rule_risk.reasons[:2],
                ],
                summary=_summary(disease, _level(probability)),
            )
        )

    status = model_status()
    status["used_targets"] = sorted(bundle["models"].keys())
    return merged, status


def _feature_row(health: HealthProfile, lifestyle: LifestyleProfile) -> dict[str, Any]:
    return {
        "sex": health.sex,
        "age_group": str(max(1, round(health.age / 5))),
        "sido": "unknown",
        "height_cm": health.height_cm,
        "weight_kg": health.weight_kg,
        "waist_cm": health.waist_cm,
        "bmi": health.bmi,
        "systolic_bp": health.systolic_bp,
        "diastolic_bp": health.diastolic_bp,
        "fasting_glucose": health.fasting_glucose,
        "total_cholesterol": health.total_cholesterol,
        "hdl": health.hdl,
        "ldl": health.ldl,
        "triglyceride": health.triglyceride,
        "smoking": lifestyle.smoking,
        "drinking": lifestyle.drinking,
    }


def _level(probability: int) -> str:
    if probability >= 60:
        return "high"
    if probability >= 35:
        return "caution"
    return "normal"


def _summary(disease: str, level: str) -> str:
    if level == "high":
        return f"{disease} 위험군 가능성이 높게 예측되었습니다."
    if level == "caution":
        return f"{disease} 주의 단계로 예측되었습니다."
    return f"{disease} 관련 입력값은 현재 낮은 위험으로 예측되었습니다."
