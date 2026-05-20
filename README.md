# 검진AI 리셋코치

건강검진 공공데이터 기반 만성질환 위험예측 및 퍼스널 개선 플랜 웹앱 MVP입니다.

## 서비스 정의

국민건강보험공단 건강검진 공공데이터로 학습 가능한 위험예측 인터페이스를 바탕으로, 사용자의 검진 수치와 생활패턴을 분석해 고혈압·당뇨·이상지질혈증 위험도를 예측하고 실생활에서 바로 실천할 수 있는 작은 개선 행동을 제안합니다.

## 제출 전략

- 공모전 제출은 웹앱 형태로 진행합니다.
- MVP는 건강검진 수치, 최근 7일 평균 걸음수, 생활패턴을 사용자가 직접 입력합니다.
- 건강 앱 자동 연동은 앱스토어/플레이스토어 승인과 네이티브 권한이 필요하므로 향후 로드맵으로 둡니다.
- 건강검진 결과지 이미지/PDF OCR 업로드는 기본 데모 모드로 제공하며, `OPENAI_API_KEY`를 넣으면 OpenAI Vision 기반 실제 추출로 전환할 수 있습니다.

## 제출용 문서

- [서비스 요약](docs/submission_overview.md)
- [AI·모델 활용 설명](docs/ai_model_strategy.md)
- [Colab 모델 학습 및 배포 연결 가이드](docs/colab_model_training.md)
- [OCR 기능 구현 방침](docs/ocr_strategy.md)
- [제출서류 작성 초안](docs/submission_form_draft.md)
- [최종 QA 체크리스트](docs/final_qa_checklist.md)

## API 키 준비

공공데이터포털 API 키를 발급받으면 `.env.example`을 복사해 `.env`를 만들고 키를 넣습니다.

```powershell
Copy-Item .env.example .env
notepad .env
```

`.env` 예시:

```env
PUBLIC_DATA_SERVICE_KEY=발급받은_공공데이터포털_서비스키
PUBLIC_DATA_BASE_URL=https://api.odcloud.kr/api
USE_DEMO_DATA=true
REQUEST_TIMEOUT_SECONDS=8
RISK_MODEL_MODE=auto
RISK_MODEL_PATH=models/risk_models.joblib
OCR_PROVIDER=demo
OCR_FALLBACK_TO_DEMO=true
OPENAI_API_KEY=
OPENAI_OCR_MODEL=gpt-4.1-mini
```

키 설정 확인:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/ready
Invoke-RestMethod http://127.0.0.1:8000/health/public-data
Invoke-RestMethod "http://127.0.0.1:8000/data/checkup/sample?per_page=2"
Invoke-RestMethod "http://127.0.0.1:8000/data/checkup/prefill"
Invoke-RestMethod "http://127.0.0.1:8000/data/group-checkup/sample?per_page=2"
python scripts/test_public_data_key.py
```

키 값은 코드에 직접 적지 않습니다. `.env` 또는 배포 플랫폼 환경변수로만 주입합니다.

PowerShell에서 `.env`가 BOM 포함 UTF-8로 저장되어도 앱은 `utf-8-sig`로 읽도록 설정되어 있습니다.

## MVP 기능

- 건강검진 수치 직접 입력
- 공공데이터포털 건강검진정보 샘플을 입력폼으로 변환
- 최근 7일 평균 걸음수 직접 입력
- 생활패턴 입력
- 개인정보 보호형 시연: 입력값은 영구 저장하지 않음
- 고혈압, 당뇨, 이상지질혈증 위험도 산출
- 공복혈당, 혈압, 지질, BMI, 허리둘레, 활동량 등 주요 위험 요인 설명
- 하루 1~2개의 무리 없는 개선 행동 추천
- 1주 단위 체크리스트 생성
- 건강검진 결과지 PDF/이미지 업로드 기반 OCR 입력 보조
- OCR 결과가 부정확해도 항목명·주변 숫자 기반 AI 매칭 파서로 검진 수치 후보 보정

## AI 활용 3단계

1. 위험도 예측 AI: 건강검진 수치와 생활패턴을 바탕으로 고혈압·당뇨·이상지질혈증 위험도를 산출합니다.
2. 설명 AI: 공복혈당, 혈압, BMI, 걸음수 등 위험도를 높인 요인을 쉬운 말로 설명합니다.
3. 퍼스널 플랜 생성 AI: 사용자의 생활패턴과 제약을 반영해 하루 1~2개의 실천 가능한 행동으로 변환합니다.

현재 MVP는 설명 가능한 규칙 기반 AI 엔진으로 동작하며, 공공데이터 기반 RandomForest/LogisticRegression 학습 파이프라인으로 확장할 수 있습니다.

## 로드맵

1. MVP: 웹앱 제출, 수동 입력, 데모 데이터
2. Next: 건강검진 결과지 OCR 정확도 검증과 사용자 확인 화면 고도화
3. Future: iOS HealthKit, Android Health Connect 연동
4. Future: 건강정보고속도로/의료 마이데이터 기반 건강검진 내역 연동

## 실행

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000`을 엽니다.

## 배포

Render 배포를 위해 `Procfile`, `render.yaml`, `.python-version`을 포함했습니다.

Render 연결 방식:

1. GitHub 저장소 `SCNULMH/healthcare`를 Render에 연결합니다.
2. Blueprint 배포를 선택하면 루트의 `render.yaml`을 사용합니다.
3. 최초 생성 시 `PUBLIC_DATA_SERVICE_KEY` 값을 Render 환경변수에 입력합니다.
4. 배포 후 `/health/ready`, `/health/public-data`, `/data/checkup/prefill`을 확인합니다.

```text
Build Command: pip install --upgrade pip && pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health/ready
Python Version: 3.10.13
```

`PUBLIC_DATA_SERVICE_KEY`는 `render.yaml`에서 `sync: false`로 선언했습니다. 저장소에는 키가 올라가지 않고, Render Dashboard에서만 입력합니다.

OCR을 실제 추출 모드로 테스트하려면 Render 환경변수에 `OCR_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_OCR_MODEL`을 설정합니다. 키가 없거나 OCR API가 실패하면 `OCR_FALLBACK_TO_DEMO=true` 설정에 따라 데모 입력값으로 자동 전환됩니다.

## PowerShell 한글 출력

파일은 UTF-8로 저장합니다. PowerShell에서 한글이 깨져 보이면 실행 전에 다음 명령을 실행합니다.

```powershell
. .\scripts\Set-Utf8Console.ps1
```

## 테스트

```powershell
python -m unittest discover -s tests
```

## 실제 공공데이터 학습

국민건강보험공단 건강검진정보 CSV를 확보한 뒤 다음 명령으로 질환별 모델을 학습할 수 있습니다.

```powershell
python scripts/fetch_public_data.py --dataset checkup --pages 1 --per-page 1000 --out .\data\health_checkup.csv
python scripts/fetch_public_data.py --dataset group-checkup --pages 1 --per-page 1000 --out .\data\group_checkup.csv
python scripts/train_risk_models.py --csv .\data\health_checkup.csv --out .\models\risk_models.joblib
```

현재 시연 앱은 공공데이터 기준값과 생활패턴 규칙을 사용한 MVP 위험 엔진으로 동작합니다. 실제 제출 전에는 위 학습 스크립트로 생성한 성능 지표를 사업계획서에 반영합니다.

## 학습 모델 런타임 분기

`RISK_MODEL_MODE`로 예측 엔진을 선택합니다.

- `auto`: 모델 파일이 있으면 학습 모델을 사용하고, 없으면 규칙 기반 엔진으로 자동 전환합니다.
- `rule`: 항상 규칙 기반 엔진만 사용합니다. Render 무료 환경이나 제출 데모에서 가장 안전합니다.
- `model`: 모델 파일 로드가 실패하면 오류를 내므로, 다른 호스팅에서 학습 모델 동작 여부를 강하게 확인할 때 사용합니다.

Colab 등 외부 환경에서 `scripts/train_risk_models.py`로 만든 `risk_models.joblib` 파일을 서버의 `RISK_MODEL_PATH` 위치에 배치하면 `/risk/predict`가 학습 모델을 우선 사용할 수 있습니다. 현재 학습 가능한 타깃은 데이터 결측 상태에 따라 달라지며, 지질 수치가 없는 표본에서는 이상지질혈증 모델은 생성되지 않고 규칙 기반 결과를 유지합니다.

## 안전 원칙

- 의료 진단 또는 치료 처방이 아닙니다.
- 극단적 식단, 격한 운동, 단기간 감량 목표를 추천하지 않습니다.
- 기저질환, 약물 복용, 알레르기가 있으면 의료진 상담을 안내합니다.
