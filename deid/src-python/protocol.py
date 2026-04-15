from __future__ import annotations

import json
import sys
import threading
from typing import Any


EVENT_READY = "READY"
EVENT_PROGRESS = "PROGRESS"
EVENT_CHUNK = "CHUNK"
EVENT_DONE = "DONE"
EVENT_ERROR = "ERROR"

LOG_TYPE_ENGINE = "engine"
LOG_TYPE_SYSTEM = "system"

_EMIT_LOCK = threading.Lock()


def emit_message(message: dict[str, Any]) -> None:
    line = json.dumps(message, ensure_ascii=False) + "\n"
    with _EMIT_LOCK:
        sys.stdout.write(line)
        sys.stdout.flush()


def emit_event(
    event_type: str, payload: dict[str, Any], message_id: str | None = None
) -> None:
    emit_message({"id": message_id, "type": event_type, "payload": payload})


def emit_error(code: str, message: str, message_id: str | None = None) -> None:
    emit_event(EVENT_ERROR, {"code": code, "message": message}, message_id=message_id)


def emit_progress(
    message: str, log_type: str, pct: int, message_id: str | None = None
) -> None:
    if log_type not in (LOG_TYPE_ENGINE, LOG_TYPE_SYSTEM):
        raise ValueError(f"Invalid log_type: {log_type}")
    emit_event(
        EVENT_PROGRESS,
        {"message": message, "log_type": log_type, "pct": max(0, min(100, pct))},
        message_id=message_id,
    )
