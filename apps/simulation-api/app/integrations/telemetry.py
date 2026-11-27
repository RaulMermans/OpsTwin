from __future__ import annotations

import json
import sys
from typing import Any


def emit(event: str, fields: dict[str, Any]) -> None:
    record = {"event": event, **fields}
    sys.stdout.write(json.dumps(record, separators=(",", ":")) + "\n")
    sys.stdout.flush()
