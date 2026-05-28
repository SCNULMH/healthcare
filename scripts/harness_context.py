from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TODO = ROOT / "TODO.json"
CHAT_DIR = ROOT / "docs" / "chat"


def _read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def _today_chat() -> Path:
    return CHAT_DIR / f"chat_{datetime.now().strftime('%y%m%d')}.md"


def _git_summary() -> str:
    try:
        log = subprocess.check_output(["git", "log", "-3", "--oneline"], cwd=ROOT, text=True, encoding="utf-8")
        status = subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True, encoding="utf-8")
    except Exception as exc:
        return f"git unavailable: {exc}"
    return f"recent commits:\n{log.strip()}\nstatus:\n{status.strip() or 'clean'}"


def session_start() -> int:
    todo = json.loads(TODO.read_text(encoding="utf-8")) if TODO.exists() else {}
    print("[SessionStart]")
    print(_git_summary())
    if todo:
        print(f"active_goal: {todo.get('active_goal')}")
        remaining = todo.get("remaining", [])
        print("remaining: " + ", ".join(item.get("id", "?") for item in remaining[:5]))
    return 0


def user_prompt_submit() -> int:
    payload = _read_stdin_json()
    prompt = str(payload.get("prompt") or payload.get("raw") or "")
    if prompt.strip() in {"챗", "챗 기록", "저장"}:
        print("Macro command detected. Use AGENTS.md macro rules.")
    print("Reminder: plan briefly, protect secrets, keep medical claims conservative, update tests for logic changes.")
    return 0


def pre_tool_use() -> int:
    payload = _read_stdin_json()
    command = str(payload.get("command") or payload.get("tool_input", {}).get("command") or payload.get("raw") or "")
    blocked = ["rm -rf", "git reset --hard", "git checkout --", "Remove-Item -Recurse -Force"]
    if any(token in command for token in blocked):
        print(f"Blocked risky command: {command}")
        return 2
    if "Get-Content" in command and "-Raw" in command:
        print("Large file read reminder: use scripts/repo_map.py or targeted ranges for 500+ line files.")
    return 0


def post_tool_use() -> int:
    payload = _read_stdin_json()
    text = str(payload.get("output") or payload.get("raw") or "")
    if len(text) > 4000:
        print(f"Output length {len(text)} chars. Summarize before reusing as context.")
    return 0


def stop() -> int:
    CHAT_DIR.mkdir(parents=True, exist_ok=True)
    path = _today_chat()
    if os.environ.get("HARNESS_SKIP_STOP_LOG") == "1":
        return 0
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with path.open("a", encoding="utf-8") as file:
        file.write(f"\n## 자동 종료 기록 - {stamp}\n")
        file.write("- 다음 시작 시 `TODO.json`과 이 파일의 마지막 섹션을 확인하세요.\n")
    print(f"stop log appended: {path}")
    return 0


COMMANDS = {
    "session_start": session_start,
    "user_prompt_submit": user_prompt_submit,
    "pre_tool_use": pre_tool_use,
    "post_tool_use": post_tool_use,
    "stop": stop,
}


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    handler = COMMANDS.get(command)
    if not handler:
        print("usage: python scripts/harness_context.py <session_start|user_prompt_submit|pre_tool_use|post_tool_use|stop>")
        return 2
    return handler()


if __name__ == "__main__":
    raise SystemExit(main())
