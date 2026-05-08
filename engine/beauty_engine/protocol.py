from __future__ import annotations

from typing import Any


def success_response(request_id: str | None, result: Any) -> dict[str, Any]:
    return {"id": request_id, "ok": True, "result": result}


def error_response(
    request_id: str | None, code: str, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "id": request_id,
        "ok": False,
        "error": {"code": code, "message": message, "details": details or {}},
    }


def event_message(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"type": "event", "event": event, "payload": payload}
