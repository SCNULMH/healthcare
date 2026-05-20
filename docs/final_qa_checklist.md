# 최종 QA 체크리스트

## 1. Render 배포 확인

- GitHub `main` 최신 커밋이 Render에 배포되었는지 확인
- Render Dashboard에서 `Auto-Deploy` 활성화 확인
- 자동 배포가 안 되면 `Manual Deploy > Deploy latest commit` 실행
- 배포 URL에서 강력 새로고침 또는 `?v=커밋해시`로 캐시 회피 확인

확인 항목:

- 첫 화면이 모바일 앱 프레임으로 보임
- 하단 네비게이션 탭이 보임
- `홈 / 기본 / 검진 / 활동 / 생활 / OCR / 분석` 탭 이동 가능
- CSS가 적용되어 카드, 버튼, 하단 탭바가 깨지지 않음

## 2. UI 안정화 확인

- 모바일 폭에서 하단 탭 7개가 가로 스크롤됨
- 하단 탭바가 입력 버튼이나 결과 카드를 가리지 않음
- 각 탭 active 상태가 정확히 변경됨
- 화면별 본문 스크롤이 가능함
- 한글 텍스트가 버튼이나 카드 밖으로 넘치지 않음
- 결과 화면에서 위험도 카드, 행동 카드, 1주 목표 카드가 지나치게 길게 밀리지 않음

## 3. 정상 시나리오

1. `데모 값 불러오기` 클릭
2. 기본·검진·활동·생활 탭 값 확인
3. `AI 위험도 분석하기` 클릭
4. 분석 결과 화면 표시 확인
5. 위험도, 주요 요인, 오늘의 개선 행동, 1주 목표 확인

## 4. 공공데이터 시나리오

1. `공공데이터 샘플 불러오기` 클릭
2. 입력값 자동 반영 확인
3. `AI 위험도 분석하기` 클릭
4. 결과 표시 확인

## 5. OCR 데모 시나리오

1. OCR 탭 이동
2. 파일 없이 `OCR 데모 흐름 보기` 클릭
3. 검진 입력값 반영 확인
4. 파일 업로드 후 데모 실행 시 상태 메시지 표시 확인
5. OCR이 확장 기능이며 사용자 확인 후 반영된다는 문구 확인

## 6. 안전 문구 확인

- 결과 화면에 의료 진단이 아니라는 문구 포함
- 추천 행동이 하루 1~2개 수준으로 제한됨
- 약 복용 중단, 치료 변경, 질병 확정 표현 없음
- 하루 한 끼, 단백질 쉐이크만 섭취, 식후 격한 러닝 등 극단적 문구 없음

## 7. 로컬 명령 검증

```powershell
python -m unittest discover -s tests
node --check static/app.js
python -m py_compile scripts/fetch_public_data.py scripts/train_risk_models.py scripts/test_public_data_key.py
```

## 8. API 검증

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/ready
Invoke-RestMethod http://127.0.0.1:8000/health/public-data
Invoke-RestMethod http://127.0.0.1:8000/data/checkup/prefill
Invoke-RestMethod http://127.0.0.1:8000/risk/demo
```

`/risk/predict`는 테스트 코드와 웹앱 정상 시나리오로 함께 확인합니다.
