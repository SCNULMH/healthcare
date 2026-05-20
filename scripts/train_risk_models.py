from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler


COLUMN_ALIASES = {
    "sex": ["sex", "성별"],
    "age_group": ["age_group", "연령대코드(5세단위)", "연령대"],
    "sido": ["sido", "시도코드", "시도"],
    "height_cm": ["height_cm", "신장(5cm단위)", "신장(5Cm단위)", "신장"],
    "weight_kg": ["weight_kg", "체중(5kg단위)", "체중(5Kg단위)", "체중"],
    "waist_cm": ["waist_cm", "허리둘레"],
    "systolic_bp": ["systolic_bp", "수축기혈압"],
    "diastolic_bp": ["diastolic_bp", "이완기혈압"],
    "fasting_glucose": ["fasting_glucose", "식전혈당(공복혈당)", "공복혈당"],
    "total_cholesterol": ["total_cholesterol", "총콜레스테롤"],
    "hdl": ["hdl", "HDL콜레스테롤"],
    "ldl": ["ldl", "LDL콜레스테롤"],
    "triglyceride": ["triglyceride", "트리글리세라이드", "중성지방"],
    "smoking": ["smoking", "흡연상태"],
    "drinking": ["drinking", "음주여부"],
}


FEATURES = [
    "sex",
    "age_group",
    "sido",
    "height_cm",
    "weight_kg",
    "waist_cm",
    "bmi",
    "systolic_bp",
    "diastolic_bp",
    "fasting_glucose",
    "total_cholesterol",
    "hdl",
    "ldl",
    "triglyceride",
    "smoking",
    "drinking",
]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for target, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df.columns:
                renamed[alias] = target
                break
    normalized = df.rename(columns=renamed)
    missing = [column for column in COLUMN_ALIASES if column not in normalized.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return normalized


def add_labels(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in FEATURES:
        if column == "bmi":
            continue
        if column not in {"sex", "age_group", "sido", "smoking", "drinking"}:
            result[column] = pd.to_numeric(result[column], errors="coerce")
    result["bmi"] = result["weight_kg"] / ((result["height_cm"] / 100) ** 2)
    result["diabetes_risk"] = (result["fasting_glucose"] >= 126).astype(int)
    result["hypertension_risk"] = (
        (result["systolic_bp"] >= 140) | (result["diastolic_bp"] >= 90)
    ).astype(int)
    lipid_columns = ["total_cholesterol", "ldl", "triglyceride", "hdl"]
    lipid_available = result[lipid_columns].notna().any(axis=1)
    lipid_risk = (
        (result["total_cholesterol"] >= 240)
        | (result["ldl"] >= 160)
        | (result["triglyceride"] >= 200)
        | (result["hdl"] < 40)
    )
    result["dyslipidemia_risk"] = lipid_risk.where(lipid_available, pd.NA)
    return result


def build_pipeline(model_name: str) -> Pipeline:
    numeric = [
        "height_cm",
        "weight_kg",
        "waist_cm",
        "bmi",
        "systolic_bp",
        "diastolic_bp",
        "fasting_glucose",
        "total_cholesterol",
        "hdl",
        "ldl",
        "triglyceride",
    ]
    categorical = ["sex", "age_group", "sido", "smoking", "drinking"]
    preprocessor = ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric,
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            ),
        ]
    )
    if model_name == "logistic":
        model = LogisticRegression(max_iter=1000, class_weight="balanced")
    else:
        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=12,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
    return Pipeline([("preprocess", preprocessor), ("model", model)])


def train_target(df: pd.DataFrame, target: str, model_name: str) -> tuple[Pipeline | None, dict]:
    dataset = df[FEATURES + [target]].dropna(subset=[target])
    class_counts = dataset[target].value_counts().to_dict()
    if len(dataset) < 20:
        return None, {
            "status": "skipped",
            "reason": "학습 표본이 20건 미만입니다.",
            "rows": int(len(dataset)),
            "class_counts": {str(key): int(value) for key, value in class_counts.items()},
        }
    if len(class_counts) < 2:
        return None, {
            "status": "skipped",
            "reason": "라벨이 단일 클래스라 분류 모델을 학습할 수 없습니다.",
            "rows": int(len(dataset)),
            "class_counts": {str(key): int(value) for key, value in class_counts.items()},
        }
    if min(class_counts.values()) < 2:
        return None, {
            "status": "skipped",
            "reason": "소수 클래스 표본이 2건 미만이라 stratified split을 수행할 수 없습니다.",
            "rows": int(len(dataset)),
            "class_counts": {str(key): int(value) for key, value in class_counts.items()},
        }
    x_train, x_test, y_train, y_test = train_test_split(
        dataset[FEATURES],
        dataset[target],
        test_size=0.2,
        stratify=dataset[target],
        random_state=42,
    )
    pipeline = build_pipeline(model_name)
    pipeline.fit(x_train, y_train)
    probabilities = pipeline.predict_proba(x_test)[:, 1]
    predictions = pipeline.predict(x_test)
    report = classification_report(y_test, predictions, output_dict=True)
    report["roc_auc"] = roc_auc_score(y_test, probabilities)
    report["status"] = "trained"
    report["rows"] = int(len(dataset))
    report["class_counts"] = {str(key): int(value) for key, value in class_counts.items()}
    return pipeline, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="국민건강보험공단 건강검진정보 CSV 경로")
    parser.add_argument("--out", default="models/risk_models.joblib")
    parser.add_argument("--model", choices=["random_forest", "logistic"], default="random_forest")
    args = parser.parse_args()

    df = pd.read_csv(args.csv, encoding="utf-8")
    df = add_labels(normalize_columns(df))
    targets = ["diabetes_risk", "hypertension_risk", "dyslipidemia_risk"]
    models = {}
    reports = {}
    for target in targets:
        model, report = train_target(df, target, args.model)
        if model is not None:
            models[target] = model
        reports[target] = report

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"features": FEATURES, "models": models, "reports": reports}, output)
    for target, report in reports.items():
        if report.get("status") == "trained":
            print(target, "roc_auc=", round(report["roc_auc"], 4), "recall=", report["1"]["recall"])
        else:
            print(target, "skipped:", report["reason"], "rows=", report["rows"])


if __name__ == "__main__":
    main()
