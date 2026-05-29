from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services import firebase_backend


def _connect() -> sqlite3.Connection | None:
    settings = get_settings()
    if settings.database_backend.lower() in {"off", "none", "memory"}:
        return None
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            bmi REAL NOT NULL,
            primary_risk_key TEXT NOT NULL,
            primary_risk_label TEXT NOT NULL,
            primary_risk_probability INTEGER NOT NULL,
            risk_payload TEXT NOT NULL,
            plan_payload TEXT NOT NULL,
            health_payload TEXT NOT NULL,
            lifestyle_payload TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_risk_history_client_created ON risk_history(client_id, created_at)")
    return conn


def save_analysis(
    *,
    client_id: str | None,
    bmi: float,
    risks: list[dict[str, Any]],
    plan: dict[str, Any],
    health: dict[str, Any],
    lifestyle: dict[str, Any],
) -> dict[str, Any] | None:
    if not client_id:
        return None
    if firebase_backend.is_enabled():
        primary = sorted(risks, key=lambda item: item["probability"], reverse=True)[0]
        previous = firebase_backend.latest_history(client_id)
        firebase_backend.save_history(
            client_id,
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "bmi": bmi,
                "primary_risk_key": primary["key"],
                "primary_risk_label": primary["label"],
                "primary_risk_probability": primary["probability"],
                "risks": risks,
                "plan": plan,
                "health": health,
                "lifestyle": lifestyle,
            },
        )
        return _comparison(previous, primary, bmi)
    conn = _connect()
    if conn is None:
        return None
    primary = sorted(risks, key=lambda item: item["probability"], reverse=True)[0]
    created_at = datetime.now(timezone.utc).isoformat()
    with conn:
        previous = _latest_row(conn, client_id)
        conn.execute(
            """
            INSERT INTO risk_history (
                client_id, created_at, bmi, primary_risk_key, primary_risk_label,
                primary_risk_probability, risk_payload, plan_payload, health_payload, lifestyle_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                client_id,
                created_at,
                bmi,
                primary["key"],
                primary["label"],
                primary["probability"],
                json.dumps(risks, ensure_ascii=False),
                json.dumps(plan, ensure_ascii=False),
                json.dumps(health, ensure_ascii=False),
                json.dumps(lifestyle, ensure_ascii=False),
            ),
        )
    return _comparison(previous, primary, bmi)


def get_history(client_id: str, limit: int = 5) -> dict[str, Any]:
    if firebase_backend.is_enabled():
        items = [_firebase_history_item(item) for item in firebase_backend.list_history(client_id, limit)]
        return {"status": "ok", "items": items, "summary": _history_summary(items)}
    conn = _connect()
    if conn is None:
        return {"status": "disabled", "items": [], "summary": None}
    rows = conn.execute(
        """
        SELECT created_at, bmi, primary_risk_key, primary_risk_label, primary_risk_probability,
               risk_payload, plan_payload
        FROM risk_history
        WHERE client_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (client_id, limit),
    ).fetchall()
    items = [_row_to_item(row) for row in rows]
    summary = _history_summary(items)
    return {"status": "ok", "items": items, "summary": summary}


def _latest_row(conn: sqlite3.Connection, client_id: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT bmi, primary_risk_label, primary_risk_probability
        FROM risk_history
        WHERE client_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (client_id,),
    ).fetchone()


def _comparison(previous: sqlite3.Row | None, primary: dict[str, Any], bmi: float) -> dict[str, Any] | None:
    if previous is None:
        return {
            "status": "first_record",
            "message": "첫 결과를 저장했습니다. 다음 결과부터 변화도 함께 보여드릴게요.",
        }
    risk_delta = int(primary["probability"]) - int(previous["primary_risk_probability"])
    bmi_delta = round(bmi - float(previous["bmi"]), 1)
    direction = "decreased" if risk_delta < 0 else "increased" if risk_delta > 0 else "same"
    return {
        "status": "compared",
        "previous_primary_label": previous["primary_risk_label"],
        "previous_primary_probability": int(previous["primary_risk_probability"]),
        "current_primary_label": primary["label"],
        "current_primary_probability": int(primary["probability"]),
        "risk_delta": risk_delta,
        "bmi_delta": bmi_delta,
        "direction": direction,
        "message": _comparison_message(risk_delta, bmi_delta),
    }


def _firebase_history_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "created_at": item["created_at"],
        "bmi": round(float(item["bmi"]), 1),
        "primary_risk_key": item["primary_risk_key"],
        "primary_risk_label": item["primary_risk_label"],
        "primary_risk_probability": int(item["primary_risk_probability"]),
        "risks": item.get("risks", []),
        "plan": item.get("plan", {}),
    }


def _comparison_message(risk_delta: int, bmi_delta: float) -> str:
    if risk_delta < 0:
        return f"이전 결과보다 주요 위험 신호가 {abs(risk_delta)}%p 낮아졌습니다."
    if risk_delta > 0:
        return f"이전 결과보다 주요 위험 신호가 {risk_delta}%p 높아졌습니다. 오늘의 작은 행동부터 다시 시작해보세요."
    if bmi_delta != 0:
        sign = "낮아졌습니다" if bmi_delta < 0 else "높아졌습니다"
        return f"주요 위험도는 유지됐고 BMI는 {abs(bmi_delta)} {sign}."
    return "이전 결과와 비슷합니다. 지금의 작은 습관을 이어가면 좋습니다."


def _row_to_item(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "created_at": row["created_at"],
        "bmi": round(float(row["bmi"]), 1),
        "primary_risk_key": row["primary_risk_key"],
        "primary_risk_label": row["primary_risk_label"],
        "primary_risk_probability": int(row["primary_risk_probability"]),
        "risks": json.loads(row["risk_payload"]),
        "plan": json.loads(row["plan_payload"]),
    }


def _history_summary(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not items:
        return None
    latest = items[0]
    oldest = items[-1]
    return {
        "count": len(items),
        "latest_primary_label": latest["primary_risk_label"],
        "latest_primary_probability": latest["primary_risk_probability"],
        "risk_delta_from_oldest": latest["primary_risk_probability"] - oldest["primary_risk_probability"],
        "bmi_delta_from_oldest": round(latest["bmi"] - oldest["bmi"], 1),
    }
