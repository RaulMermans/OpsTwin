import hashlib
import json
from pathlib import Path
from typing import Any

from app.domain.comparison import ScenarioComparisonRequest
from app.domain.models import OperationalModel
from app.scenarios.coordinator import run_scenario_comparison


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_gm042_product_fixtures_are_canonical_and_bounded(
    repository_root: Path,
) -> None:
    product_dir = repository_root / "examples" / "product"
    baseline_data = load_json(product_dir / "support-operations-baseline.json")
    request_data = load_json(product_dir / "support-operations-comparison.json")

    baseline = OperationalModel.model_validate(baseline_data)
    request = ScenarioComparisonRequest.model_validate(request_data)

    assert request.baseline_model == baseline
    assert baseline.sources[0].arrival.type == "poisson"
    assert [stage.id for stage in baseline.stages] == [
        "triage",
        "level-1",
        "level-2",
        "quality-check",
    ]
    assert [scenario.id for scenario in request.scenarios] == [
        "add-level-1-agent",
        "faster-triage",
    ]
    assert request.execution.base_seed == 20_260_716
    assert request.execution.run_count == 50
    assert request.representative_evidence.detail_mode == "sampled"
    work_units = (
        baseline.sources[0].item_count
        * request.execution.run_count
        * (len(request.scenarios) + 1)
    )
    assert work_units == 15_000


def test_product_comparison_is_reproducible_and_below_payload_guard(
    repository_root: Path,
) -> None:
    request = ScenarioComparisonRequest.model_validate(
        load_json(
            repository_root
            / "examples"
            / "product"
            / "support-operations-comparison.json"
        )
    )

    first = run_scenario_comparison(request)
    second = run_scenario_comparison(request)
    payload = first.model_dump_json(by_alias=True)

    assert payload == second.model_dump_json(by_alias=True)
    assert len(payload.encode("utf-8")) < 1_000_000
    assert first.execution.ordinary_run_retained_event_count == 0
    assert first.execution.maximum_simultaneously_retained_event_rich_results <= 2
    assert first.integrity.status == "passed"
    assert hashlib.sha256(payload.encode("utf-8")).hexdigest()
