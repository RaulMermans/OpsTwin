from __future__ import annotations

from typing import Any

from app.integrations.telemetry import emit as emit_line


def emit_calibration(event: str, fields: dict[str, Any]) -> None:
    emit_line(event, fields)
