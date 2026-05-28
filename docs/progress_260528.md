# 의료 공모전 진행상황 기록

작성일: 2026-05-28

## 현재 상태

- 서비스명: 검진AI 리셋코치
- 로컬 실행 주소: `http://127.0.0.1:8004`
- 저장소: `https://github.com/SCNULMH/healthcare.git`
- 최신 작업 커밋: `Harden medical fallback and OCR unknown handling`
- 데이터 저장: Firebase 연동 기준
- Render 배포 기준 환경변수:
  - `DATABASE_BACKEND=firebase`
  - `FIREBASE_CREDENTIALS_JSON=서비스계정 JSON 전체`
  - `FIREBASE_PROJECT_ID=checkup-70a1e`
  - `FIREBASE_WEB_APP_ID=1:605150906055:web:6021dd1c404c7739cde0e2`

## 완료된 주요 기능

### 하네스/컨텍스트 관리

- 의료 앱 전용 `AGENTS.md` 추가
- `.codex/AGENTS.md`를 의료 공모전 기준으로 교체
- `.codex/hooks.json`을 repo-local hook runner 기준으로 정리
- `TODO.json`에 현재 목표, 완료 항목, 남은 작업을 기계 판독용으로 기록
- `챗`, `챗 기록`, `저장` macro command 규칙 정의
- `scripts/repo_map.py`로 긴 Python 파일 전체 조회 대신 class/function map 확인 가능
- `docs/harness_architecture.md`, `docs/chat/chat_260528.md`에 하네스 설계와 진행 기록 추가

### 계정/개인정보

- Firebase 기반 계정 생성, 로그인, 프로필 저장 흐름 구현
- 로그인 성공 시 아이디/비밀번호 입력창 숨김
- 로그아웃 버튼 추가
- 로그인하지 않은 상태에서 진단결과 저장 시 저장을 막고 로그인 안내
- 개인정보 입력 항목 확장:
  - 이름
  - 출생연도
  - 성별
  - 나이
  - 키
  - 체중
  - 허리둘레
  - 질환/복용약/알레르기
- 마이페이지 개인정보 상단에 `나의 기본 정보를 입력해 주세요` 안내 추가
- 작은 `불러오기` 버튼으로 기본정보 탭의 나이/성별/키/체중/허리둘레를 개인정보 입력칸에 복사
- 성별 수정 시 404가 발생하던 흐름을 완화하기 위해 프로필 업데이트 payload와 저장 로직 보강

### 검진 입력

- 혈압 아이콘을 `❤️`로 변경
- 혈당 아이콘 유지
- 지질 아이콘을 `🟡`로 변경
- 검진탭/생활탭의 평균 설명 제거
- 평균 기준은 결과 화면에서만 표시
- 검진 세부 항목별 `모름` 체크 구현:
  - 수축기혈압
  - 이완기혈압
  - 공복혈당
  - 총콜레스테롤
  - HDL
  - LDL
  - 중성지방
- `모름` 체크 시 해당 항목만 `null` 처리
- 일부 항목만 모르는 경우 입력된 직접값과 생활 기준을 함께 반영
- 모든 지질 항목을 모르는 경우 지질 직접값 판단을 제외하고 외식/야식/운동/걸음수 기준으로 추정
- 혈압은 수축기/이완기 중 하나만 모르는 경우에도 입력된 나머지 혈압값은 직접 판단에 반영

### 생활 입력

- 아침식사를 `규칙적/가끔/거의 안 함` 선택식에서 `주간 아침식사 횟수` 숫자 입력으로 변경
- 음주 입력을 세분화:
  - 주간 음주 횟수
  - 월간 추가 음주 횟수
  - 1회 평균 음주량(잔)
- 기존 `안 함/가벼움/보통/잦음`은 사용자 입력값이 아니라 내부 분류 기준으로 사용
- 음주 분류 기준:
  - 주/월 음주가 없으면 `none`
  - 월 환산 3회 이하이고 1회 2잔 이하면 `light`
  - 월 환산 8회 이하이고 1회 4잔 이하면 `moderate`
  - 그 이상은 `heavy`
- `moderate/heavy` 음주는 혈압 생활요인 점수에 반영
- `식사 준비 가능` 항목 제거

### 결과 화면

- 결과 저장은 버튼을 눌렀을 때만 수행
- 결과탭을 `기준 / 위험도 / 신뢰도 / 추천 / 1주`로 분리
- AI 개인화 추천 카드에서 난이도 표시 제거
- 기준 탭에 생활요인 점수 기준 추가:
  - 단 음료 +8
  - 운동 부족 +7
  - 5,000보 미만 +5
  - 외식 +7
  - 음주 보통 +6
  - 음주 잦음 +8
  - 야식 +5
  - 지질 관련 외식 +6
- 결과 상단에 개인정보/기본정보 기준 연령대와 성별 평균 표시
- 결과 상단에 음주 `안 함/가벼움/보통/잦음` 변환 기준을 칩 형태로 표시
- 건강 리셋 점수 설명창 추가
- 점수 하단에 `70~100 안정권`, `40~69 주의권`, `0~39 위험군` 구간 표시

### OCR/공공데이터/모델

- OCR 결과를 자동 입력 수준으로 검진 수치 화면에 반영
- OCR 결과는 사용자가 확인 후 분석하도록 흐름 구성
- 업로드 원본은 영구 저장하지 않는 방향 유지
- OCR이 읽지 못한 검진 세부항목은 데모값으로 채우지 않고 항목별 `모름`으로 자동 연동
- 공공데이터 샘플 불러오기 유지
- 모델이 사용 가능하면 학습 모델을 사용하고, 검진 핵심값이 `모름`이면 설명 가능한 규칙 기반 엔진으로 fallback
- 신뢰도/평균 비교 카드 유지
- Firebase는 `DATABASE_BACKEND=firebase`인데 credential이 없으면 앱이 즉시 뻗지 않도록 sqlite fallback 상태를 노출

## 최근 커밋 기록

- `95faacb` Move profile import control inline
- 이번 작업: 결측치 fallback/음주 변환 테스트, OCR 모름 자동 연동, Firebase credential fallback 보강
- `a79b657` Add profile basic info import fields
- `389977f` Fix unknown checkbox sizing
- `59d6ad6` Add account logout control
- `a7b1066` Require login before saving and support field unknowns
- `217bc8b` Refine lifestyle inputs and unknown checkup handling
- `a11726a` Handle unknown lipid inputs and personal benchmarks
- `c5adeba` Make auth hiding and result tabs explicit
- `af6d8dd` Refine diagnosis tabs and benchmarks

## 검증 현황

- `node --check static/app.js` 통과
- `python -m unittest discover -s tests` 23개 통과
- 로컬 서버 `http://127.0.0.1:8004`에서 주요 UI 반영 확인
- GitHub `main` 브랜치 push 완료

## 현재 개선점

- Firebase 저장 흐름은 구현되어 있으나, 실제 Render 환경에서는 반드시 `FIREBASE_CREDENTIALS_JSON`을 정확히 넣어야 함
- 개인정보/진단결과 저장 UX는 동작하지만, 저장 성공 후 시각적 피드백을 더 명확하게 만들 수 있음
- 결과의 평균 기준은 현재 앱 내 기준표 기반이므로, 제출 전 공공데이터 기반 평균 산출 근거를 문서화하면 신뢰도가 좋아짐
- 음주 영향은 점수에 반영되고, 결과 카드에서 `주간/월간/잔 수`가 어떻게 내부 분류로 바뀌었는지 확인 가능
- `모름` 체크가 많을 때 신뢰도 점수와 안내문을 더 눈에 띄게 표시하는 개선 여지는 남아 있음
- 개인정보와 기본정보가 양방향 동기화되지는 않음. 현재는 기본정보에서 개인정보로 불러오는 단방향
- OCR 결과가 비어 있거나 정확히 읽히지 않은 항목은 항목별 `모름` 자동 체크로 연동

## 남은 작업 제안

1. Render 배포 환경변수 최종 점검
2. Firebase 실제 계정 생성/로그인/로그아웃/재로그인 저장 유지 테스트
3. 모바일 화면에서 검진탭 `모름` 체크박스 크기와 줄바꿈 재확인
4. 결과탭 기준 카드 문구를 심사위원용으로 더 명확하게 다듬기
5. 제출용 캡처 목록 정리:
   - 홈
   - 기본정보
   - 검진 입력
   - 생활 입력
   - OCR
   - 결과 기준 탭
   - 위험도 탭
   - 신뢰도 탭
   - 로그인/저장 기록
6. 사업계획서에 넣을 기술 설명 정리:
   - 공공데이터 기반 검진 위험 추정
   - 개인정보 기반 개인화
   - 모름/결측 입력 처리
   - Firebase 저장
   - OCR 자동 입력
   - 설명 가능한 AI fallback
