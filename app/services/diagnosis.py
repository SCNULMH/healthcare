from dataclasses import dataclass
from typing import Literal


Sex = Literal["male", "female"]
Level = Literal["normal", "caution", "high"]


@dataclass(frozen=True)
class HealthProfile:
    age: int
    sex: Sex
    height_cm: float
    weight_kg: float
    waist_cm: float
    systolic_bp: int
    diastolic_bp: int
    fasting_glucose: int
    total_cholesterol: int
    hdl: int
    ldl: int
    triglyceride: int

    @property
    def bmi(self) -> float:
        return self.weight_kg / ((self.height_cm / 100) ** 2)


@dataclass(frozen=True)
class LifestyleProfile:
    breakfast: Literal["regular", "sometimes", "rarely"]
    sugary_drinks_per_week: int
    late_meals_per_week: int
    exercise_per_week: int
    eating_out_per_week: int
    sleep_hours: float
    avg_steps: int
    smoking: Literal["never", "past", "current"]
    drinking: Literal["none", "light", "moderate", "heavy"]
    available_minutes_per_day: int
    can_prepare_meals: bool


@dataclass(frozen=True)
class RiskResult:
    key: str
    label: str
    level: Level
    probability: int
    reasons: list[str]
    summary: str

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "level": self.level,
            "probability": self.probability,
            "reasons": self.reasons,
            "summary": self.summary,
        }


def evaluate_health_risks(health: HealthProfile, lifestyle: LifestyleProfile) -> list[RiskResult]:
    return [
        _diabetes_risk(health, lifestyle),
        _hypertension_risk(health, lifestyle),
        _dyslipidemia_risk(health, lifestyle),
    ]


def create_personal_plan(
    health: HealthProfile,
    lifestyle: LifestyleProfile,
    risks: list[RiskResult],
) -> dict:
    priority = sorted(risks, key=lambda item: item.probability, reverse=True)[:2]
    actions: list[dict] = []

    for risk in priority:
        actions.extend(_actions_for_risk(risk.key, health, lifestyle))

    safe_actions = _dedupe_actions(actions)[:2]
    weekly_goals = _weekly_goals(priority, health, lifestyle)

    return {
        "title": "이번 주는 생활패턴을 조금만 바꾸는 것부터 시작하세요.",
        "focus": [risk.label for risk in priority],
        "today_actions": safe_actions,
        "weekly_goals": weekly_goals[:3],
        "safety_note": (
            "무리한 식단 제한이나 격한 운동은 권하지 않습니다. "
            "기저질환, 약물 복용, 알레르기가 있다면 의료진과 상담하세요."
        ),
    }


def _diabetes_risk(health: HealthProfile, lifestyle: LifestyleProfile) -> RiskResult:
    score = 18
    reasons: list[str] = []

    if health.fasting_glucose >= 126:
        score += 42
        reasons.append("공복혈당이 당뇨 위험 기준 이상입니다.")
    elif health.fasting_glucose >= 100:
        score += 24
        reasons.append("공복혈당이 주의 범위입니다.")

    score += _bmi_score(health, reasons)
    if health.waist_cm >= _waist_high_cutoff(health.sex):
        score += 8
        reasons.append("허리둘레가 복부비만 위험 범위입니다.")
    if lifestyle.sugary_drinks_per_week >= 5:
        score += 8
        reasons.append("단 음료 섭취가 잦습니다.")
    if lifestyle.exercise_per_week <= 1:
        score += 7
        reasons.append("주간 운동 빈도가 낮습니다.")
    if lifestyle.avg_steps < 5000:
        score += 5
        reasons.append("최근 7일 평균 걸음수가 낮습니다.")

    probability = min(score, 95)
    level = _level(probability)
    return RiskResult(
        key="diabetes",
        label="당뇨 위험군",
        level=level,
        probability=probability,
        reasons=reasons or ["검진 수치가 전반적으로 안정 범위에 가깝습니다."],
        summary=_summary("당뇨", level),
    )


def _hypertension_risk(health: HealthProfile, lifestyle: LifestyleProfile) -> RiskResult:
    score = 16
    reasons: list[str] = []

    if health.systolic_bp >= 140 or health.diastolic_bp >= 90:
        score += 43
        reasons.append("혈압이 고혈압 위험 기준 이상입니다.")
    elif health.systolic_bp >= 130 or health.diastolic_bp >= 80:
        score += 25
        reasons.append("혈압이 주의 범위입니다.")

    score += _bmi_score(health, reasons)
    if lifestyle.eating_out_per_week >= 5:
        score += 7
        reasons.append("외식 빈도가 높아 나트륨 섭취가 늘 수 있습니다.")
    if lifestyle.drinking in {"moderate", "heavy"}:
        score += 6
        reasons.append("음주 습관이 혈압 관리에 부담이 될 수 있습니다.")
    if lifestyle.exercise_per_week <= 1:
        score += 5
        reasons.append("규칙적인 신체활동이 부족합니다.")
    if lifestyle.avg_steps < 5000:
        score += 4
        reasons.append("평균 걸음수가 낮아 활동량 보강이 필요합니다.")

    probability = min(score, 95)
    level = _level(probability)
    return RiskResult(
        key="hypertension",
        label="고혈압 위험군",
        level=level,
        probability=probability,
        reasons=reasons or ["혈압과 생활습관 지표가 큰 위험 신호 없이 입력되었습니다."],
        summary=_summary("고혈압", level),
    )


def _dyslipidemia_risk(health: HealthProfile, lifestyle: LifestyleProfile) -> RiskResult:
    score = 15
    reasons: list[str] = []

    lipid_flags = [
        health.total_cholesterol >= 240,
        health.ldl >= 160,
        health.triglyceride >= 200,
        health.hdl < 40,
    ]
    caution_flags = [
        health.total_cholesterol >= 200,
        health.ldl >= 130,
        health.triglyceride >= 150,
        health.hdl < 50,
    ]

    if any(lipid_flags):
        score += 40
        reasons.append("콜레스테롤 또는 중성지방 수치가 위험 범위입니다.")
    elif any(caution_flags):
        score += 22
        reasons.append("지질 수치 중 일부가 주의 범위입니다.")

    score += _bmi_score(health, reasons)
    if lifestyle.eating_out_per_week >= 5:
        score += 6
        reasons.append("외식 빈도가 높아 포화지방 섭취가 늘 수 있습니다.")
    if lifestyle.late_meals_per_week >= 3:
        score += 5
        reasons.append("야식 빈도가 높습니다.")
    if lifestyle.exercise_per_week <= 1:
        score += 5
        reasons.append("신체활동이 부족합니다.")
    if lifestyle.avg_steps < 5000:
        score += 4
        reasons.append("최근 활동량이 낮습니다.")

    probability = min(score, 95)
    level = _level(probability)
    return RiskResult(
        key="dyslipidemia",
        label="이상지질혈증 위험군",
        level=level,
        probability=probability,
        reasons=reasons or ["지질 관련 입력값이 안정 범위에 가깝습니다."],
        summary=_summary("이상지질혈증", level),
    )


def _actions_for_risk(key: str, health: HealthProfile, lifestyle: LifestyleProfile) -> list[dict]:
    if key == "diabetes":
        return _diabetes_actions(lifestyle)
    if key == "hypertension":
        return _hypertension_actions(lifestyle)
    return _dyslipidemia_actions(lifestyle)


def _diabetes_actions(lifestyle: LifestyleProfile) -> list[dict]:
    actions = []
    if lifestyle.sugary_drinks_per_week:
        actions.append(_action("단 음료 1잔 줄이기", "점심 후 달달한 커피나 탄산음료를 무가당 음료로 바꿔보세요.", "낮음"))
    if lifestyle.exercise_per_week <= 2:
        actions.append(_action("식후 10분 걷기", "뛰지 말고 저녁 식사 후 10분만 천천히 걸어보세요.", "낮음"))
    actions.append(_action("식사 전 채소 먼저", "식사 시작 전에 방울토마토 5알이나 채소 한 접시를 먼저 먹어보세요.", "낮음"))
    if lifestyle.breakfast != "regular":
        actions.append(_action("단백질 1가지 추가", "아침이나 점심에 계란, 두부, 닭가슴살 중 편한 것 1가지를 더해보세요.", "낮음"))
    return actions


def _hypertension_actions(lifestyle: LifestyleProfile) -> list[dict]:
    actions = []
    if lifestyle.eating_out_per_week >= 3:
        actions.append(_action("국물 절반 남기기", "찌개나 국을 먹을 때 국물은 절반만 먹는 방식으로 나트륨을 줄여보세요.", "낮음"))
    if lifestyle.drinking in {"moderate", "heavy"}:
        actions.append(_action("술자리 물 한 컵 규칙", "술 한 잔 사이에 물 한 컵을 마시고, 이번 주 술자리를 1회 줄여보세요.", "중간"))
    actions.append(_action("계단 1층만 걷기", "엘리베이터 대신 계단 1층만 이용하는 정도로 시작하세요.", "낮음"))
    return actions


def _dyslipidemia_actions(lifestyle: LifestyleProfile) -> list[dict]:
    actions = []
    if lifestyle.late_meals_per_week:
        actions.append(_action("야식 1회 줄이기", "이번 주 야식 중 1번만 과일, 견과류 소량, 물로 바꿔보세요.", "중간"))
    if lifestyle.eating_out_per_week >= 3:
        actions.append(_action("튀김 대신 구이 선택", "외식 메뉴를 고를 때 튀김보다 구이, 찜, 국물 적은 메뉴를 먼저 고르세요.", "낮음"))
    actions.append(_action("식이섬유 더하기", "한 끼에 채소 반 접시나 잡곡밥을 조금 추가해보세요.", "낮음"))
    return actions


def _weekly_goals(priority: list[RiskResult], health: HealthProfile, lifestyle: LifestyleProfile) -> list[str]:
    goals = []
    keys = {risk.key for risk in priority}
    if "diabetes" in keys:
        goals.append(f"단 음료 {lifestyle.sugary_drinks_per_week}잔 중 2~3잔 줄이기")
        goals.append("식후 10분 걷기 주 3회 실천")
    if "hypertension" in keys:
        goals.append("국물 있는 음식은 국물 절반 남기기 주 3회")
    if "dyslipidemia" in keys:
        goals.append("튀김 메뉴를 구이·찜 메뉴로 주 2회 바꾸기")
    if health.bmi >= 25:
        goals.append("체중 감량보다 식사·걷기 기록을 1주일 유지하기")
    return goals or ["현재 습관을 유지하면서 주 3회 10분 걷기"]


def _action(title: str, detail: str, difficulty: str) -> dict:
    return {"title": title, "detail": detail, "difficulty": difficulty}


def _dedupe_actions(actions: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for action in actions:
        if action["title"] not in seen:
            seen.add(action["title"])
            result.append(action)
    return result


def _bmi_score(health: HealthProfile, reasons: list[str]) -> int:
    if health.bmi >= 30:
        reasons.append("BMI가 비만 위험 범위입니다.")
        return 12
    if health.bmi >= 25:
        reasons.append("BMI가 과체중 범위입니다.")
        return 8
    return 0


def _waist_high_cutoff(sex: Sex) -> int:
    return 90 if sex == "male" else 85


def _level(probability: int) -> Level:
    if probability >= 60:
        return "high"
    if probability >= 35:
        return "caution"
    return "normal"


def _summary(disease: str, level: Level) -> str:
    if level == "high":
        return f"{disease} 위험군 가능성이 높게 예측되었습니다."
    if level == "caution":
        return f"{disease} 주의 단계로 예측되었습니다."
    return f"{disease} 관련 입력값은 현재 낮은 위험으로 예측되었습니다."
