# 하네스 엔지니어링 설계

작성일: 2026-05-28

## 목표

검진AI 리셋코치 개발에서 매 턴 반복되는 맥락 로딩을 줄이고, 보안/검증/기록을 자동화한다. 사람용 설명은 `README.md`와 제출 문서에 두고, 에이전트용 결정 규칙은 `AGENTS.md`, `TODO.json`, `docs/chat/`에 짧게 유지한다.

## 파일 역할

| 파일 | 대상 | 역할 |
| --- | --- | --- |
| `AGENTS.md` | 에이전트 | 빌드/테스트, 구조, 금지 규칙, macro command |
| `.codex/AGENTS.md` | Codex 로컬 | 루트 지침과 같은 내용의 로컬 런타임 지침 |
| `.codex/hooks.json` | Codex 로컬 | lifecycle hook 연결 |
| `TODO.json` | 에이전트 | 목표, 완료, 남은 작업의 기계 판독용 상태 |
| `docs/progress_260528.md` | 사람/에이전트 | 상세 진행상황과 개선점 |
| `docs/chat/chat_YYMMDD.md` | 연속성 | `챗`, `챗 기록` 명령용 최근 작업 로그 |
| `scripts/harness_context.py` | hook runner | SessionStart, prompt, tool, stop 처리 |
| `scripts/repo_map.py` | token saver | 긴 Python 파일 대신 class/function map 출력 |

## Macro Command

`챗`

- 오늘 또는 최신 `docs/chat/chat_YYMMDD.md` 마지막 섹션을 읽는다.
- `TODO.json`의 `remaining`을 함께 확인한다.
- 이전 기록과 남은 과정을 먼저 요약한 뒤 작업을 이어간다.

`챗 기록`

- 현재까지 진행상황, 변경 파일, 테스트 결과, blocker, 다음 작업을 오늘 chat log에 append한다.
- 장기 작업 후에는 사용자가 명령하지 않아도 같은 형식으로 기록한다.

`저장`

- `python -m unittest discover -s tests`
- `node --check static/app.js`
- 필요 시 진행 문서 갱신
- `git add`, `git commit`, `git push`

## Lifecycle Hook 설계

| Hook | 동작 |
| --- | --- |
| SessionStart | 최근 git commit/status와 `TODO.json` active goal 출력 |
| UserPromptSubmit | macro 감지, 보안/의료표현/테스트 리마인더 출력 |
| PreToolUse | 위험 명령 차단, 큰 파일 조회 경고 |
| PermissionRequest | shell 안전성 점검 재사용 |
| PostToolUse | 큰 출력은 요약하라는 경고 |
| Stop | 오늘 chat log에 continuity note append |

## Token 정책

- `rg`/`rg --files`를 우선 사용한다.
- 500라인 이상 파일은 전체 조회하지 않고 `scripts/repo_map.py` 또는 필요한 range만 읽는다.
- 진행상황은 긴 대화 대신 `TODO.json`과 chat log로 복원한다.
- 증빙/출처/테스트 결과는 짧은 alias 또는 bullet로만 유지한다.

## 보안 정책

- `.env`, Firebase admin JSON, API key, 사용자 업로드 원본, SQLite DB는 커밋하지 않는다.
- OCR 원본은 서버/DB에 영구 저장하지 않는다.
- Firebase credential 누락 시 앱 전체 장애가 아니라 상태 응답과 fallback으로 처리한다.
- 의료 문구는 진단/치료 확정 표현을 피하고 위험 안내로 제한한다.

## 다음 확장

1. `scripts/harness_context.py pre_tool_use`에 파일 라인 수 감지와 RepoMap 자동 출력 추가.
2. JS/CSS도 간단한 symbol map 또는 section map을 만들기.
3. `TODO.json` 갱신 helper 추가.
4. 서버단 Firebase ID token 검증 작업과 연결해 보안 hook checklist 확장.
