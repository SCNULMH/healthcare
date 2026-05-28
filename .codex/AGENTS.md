# 검진AI 리셋코치 Agent Directives

## Scope
- Product: FastAPI + static web MVP for medical contest submission.
- Human docs: read `README.md` only when business context is needed; do not preload it.
- Current progress SSOT: `docs/progress_260528.md`, `TODO.json`, latest `docs/chat/chat_YYMMDD.md`.

## Commands
- Test: `python -m unittest discover -s tests`
- JS syntax: `node --check static/app.js`
- Run server: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8004`
- Health: `Invoke-WebRequest http://127.0.0.1:8004/health/ready -UseBasicParsing`

## Layout
- `app/routers/`: FastAPI routes, async endpoints, Pydantic input validation.
- `app/services/`: diagnosis, model, OCR, Firebase/SQLite, public-data logic.
- `static/`: mobile-first UI. Keep controls touch-safe and text non-overlapping.
- `scripts/`: training, public-data, harness utility scripts.
- `docs/`: submission notes, progress, chat logs.

## Safety Rules
- Never commit `.env`, Firebase admin JSON, API keys, uploaded medical images, or SQLite data.
- Uploaded OCR files must be processed in memory only; no persistent original-image storage.
- Render filesystem is ephemeral. Durable user data belongs in Firebase or configured DB.
- If `DATABASE_BACKEND=firebase` but credentials are missing, degrade gracefully.
- Medical output is risk guidance, not diagnosis. Do not imply treatment or certainty.

## Coding Rules
- Prefer small scoped edits following existing style.
- Use `apply_patch` for manual file edits.
- Keep API contracts stable for `static/app.js`.
- For unknown checkup fields, set only that field to `null`; do not discard known sibling values.
- Add/adjust tests when changing diagnosis, OCR, auth, Firebase, or save behavior.

## Context Economy
- Use `rg`/`rg --files` first.
- Do not read files over 500 lines in full. Use `scripts/repo_map.py <file>` or targeted ranges.
- Summarize large outputs; avoid pasting secrets or full API payloads.
- Use `TODO.json` and chat logs instead of carrying long conversational history.

## Macro Commands
- `챗`: read the latest `docs/chat/chat_YYMMDD.md` tail, report previous state, then continue the remaining work.
- `챗 기록`: append current progress, changed files, tests, blockers, and remaining steps to today`s chat log.
- `저장`: run tests, update progress docs if needed, commit, push, then report commit hash.

## Git
- Work on `main`, remote `origin`.
- Do not revert user changes.
- After user-requested implementation, push to GitHub unless explicitly told not to.
