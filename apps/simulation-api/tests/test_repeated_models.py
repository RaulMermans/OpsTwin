from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.repeated import RepeatedSimulationRequest


def test_repeated_request_defaults(support_model_data: dict[str, Any]) -> None:
    request = RepeatedSimulationRequest(model=support_model_data, baseSeed=42)

    assert request.schema_version == "0.4.0"
    assert request.run_count == 100
    assert request.confidence_level == 0.95
    assert request.minimum_successful_run_ratio == 1.0
    assert request.representative_run.detail_mode == "sampled"
    assert request.representative_run.sampled_item_limit == 25


@pytest.mark.parametrize("run_count", [1, 501])
def test_repeated_request_rejects_run_count_bounds(
    support_model_data: dict[str, Any], run_count: int
) -> None:
    with pytest.raises(ValidationError):
        RepeatedSimulationRequest(
            model=support_model_data, baseSeed=42, runCount=run_count
        )


@pytest.mark.parametrize("confidence", [0.8, 0.94, 1.0])
def test_repeated_request_rejects_unsupported_confidence(
    support_model_data: dict[str, Any], confidence: float
) -> None:
    with pytest.raises(ValidationError):
        RepeatedSimulationRequest(
            model=support_model_data, baseSeed=42, confidenceLevel=confidence
        )


@pytest.mark.parametrize("ratio", [0.49, 1.01])
def test_repeated_request_rejects_success_ratio_bounds(
    support_model_data: dict[str, Any], ratio: float
) -> None:
    with pytest.raises(ValidationError):
        RepeatedSimulationRequest(
            model=support_model_data,
            baseSeed=42,
            minimumSuccessfulRunRatio=ratio,
        )


def test_representative_sample_limit_is_mode_specific(
    support_model_data: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError, match="sampledItemLimit"):
        RepeatedSimulationRequest(
            model=support_model_data,
            baseSeed=42,
            representativeRun={"detailMode": "full", "sampledItemLimit": 2},
        )


def test_threshold_validation_is_metric_specific(
    support_model_data: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        RepeatedSimulationRequest(
            model=support_model_data,
            baseSeed=42,
            thresholds={"minimumSlaAttainment": 1.1},
        )
    with pytest.raises(ValidationError):
        RepeatedSimulationRequest(
            model=support_model_data,
            baseSeed=42,
            thresholds={"maximumAverageCycleTime": -1},
        )
