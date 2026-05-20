# Colab 모델 학습 및 배포 연결 가이드

## 1. 목적

로컬 또는 Colab에서 국민건강보험공단 건강검진정보 CSV로 모델을 학습한 뒤, 생성된 `risk_models.joblib` 파일을 서버에 배치해 `/risk/predict`에서 학습 모델을 사용하도록 테스트합니다.

기본 운영은 안전한 `auto` 모드입니다. 모델 파일이 없거나 로드에 실패하면 규칙 기반 엔진으로 자동 전환됩니다.

## 2. Colab 학습 흐름

1. GitHub 저장소를 Colab에 복제합니다.

```bash
git clone https://github.com/SCNULMH/healthcare.git
cd healthcare
pip install -r requirements.txt
```

2. 공공데이터 CSV를 업로드하거나 API로 내려받습니다.

```bash
python scripts/fetch_public_data.py --dataset checkup --pages 3 --per-page 1000 --out data/health_checkup_training.csv
```

3. 모델을 학습합니다.

```bash
python scripts/train_risk_models.py --csv data/health_checkup_training.csv --out models/risk_models.joblib
```

4. 출력 로그에서 학습된 타깃을 확인합니다.

예상 예시:

```text
diabetes_risk roc_auc= ...
hypertension_risk roc_auc= ...
dyslipidemia_risk skipped: ...
```

지질 수치가 비어 있는 CSV에서는 이상지질혈증 모델이 생성되지 않을 수 있습니다. 이 경우 앱은 이상지질혈증만 규칙 기반 결과를 유지합니다.

## 3. 서버 적용 방법

서버에 모델 파일을 둘 수 있는 호스팅이면 `models/risk_models.joblib` 위치에 업로드합니다.

환경변수:

```env
RISK_MODEL_MODE=auto
RISK_MODEL_PATH=models/risk_models.joblib
```

모델 파일이 실제로 동작하는지 강하게 테스트하려면:

```env
RISK_MODEL_MODE=model
```

이 모드에서 모델 파일이 없거나 로드에 실패하면 `/risk/predict`가 오류를 냅니다. 무료 호스팅이나 제출 데모에서는 `auto` 또는 `rule`을 권장합니다.

## 4. Render 무료 환경 주의

Render 무료 환경에서는 모델 파일을 저장소에 포함하지 않으면 배포 후 파일이 없습니다. 현재 저장소는 `models/`를 `.gitignore` 처리하므로 기본 배포에서는 모델 파일이 올라가지 않습니다.

안전한 Render 설정:

```env
RISK_MODEL_MODE=auto
USE_DEMO_DATA=true
```

이렇게 하면 모델 파일이 없어도 규칙 기반 엔진으로 전환되고, 공공데이터 API가 실패해도 데모 데이터로 샘플 입력이 유지됩니다.

## 5. 예측 엔진 확인

웹앱 결과 화면의 `예측 엔진` 문구에서 현재 사용된 엔진을 확인할 수 있습니다.

API로 확인:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/risk/metadata
```

`model.status`가 `loaded`이면 학습 모델 파일이 로드된 상태입니다. `missing`이면 모델 파일이 없어서 규칙 기반 엔진을 사용합니다.

## 6. 실패 시 데모 모드

서버에서 모델 파일이 없거나 공공데이터 API 호출이 불안정하면 다음 설정으로 안전하게 시연합니다.

```env
RISK_MODEL_MODE=rule
USE_DEMO_DATA=true
```

이 설정은 외부 API와 모델 파일에 의존하지 않고, 규칙 기반 AI 엔진과 데모 공공데이터 샘플로 앱 흐름을 유지합니다.
