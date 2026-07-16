from typing import Any

import pytest

from app.domain.models import OperationalModel, ResultDetailConfig
from app.engine import context as context_module
from app.engine.events import EventRecorder
from app.engine.simulator import run_simulation


@pytest.mark.parametrize(
    ("detail", "expected_retained"),
    [
        (ResultDetailConfig(mode="summary"), 0),
        (ResultDetailConfig(mode="sampled", sampledItemLimit=2), 16),
        (ResultDetailConfig(mode="full"), 164),
    ],
)
def test_recorder_retains_only_requested_event_evidence(
    support_model_data: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    detail: ResultDetailConfig,
    expected_retained: int,
) -> None:
    recorders: list[EventRecorder] = []

    class CapturingRecorder(EventRecorder):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)  # type: ignore[arg-type]
            recorders.append(self)

    monkeypatch.setattr(context_module, "EventRecorder", CapturingRecorder)
    result = run_simulation(
        OperationalModel.model_validate(support_model_data),
        result_detail=detail,
    )

    assert len(recorders) == 1
    assert len(recorders[0].events) == expected_retained
    assert len(result.events) == expected_retained
    assert result.result_detail.total_event_count == 164
