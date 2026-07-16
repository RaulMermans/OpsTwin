from pathlib import Path

from app.cli import load_model
from app.engine.simulator import run_simulation


def test_seeded_support_example_has_exact_reproducible_summary(
    repository_root: Path,
) -> None:
    model = load_model(repository_root / "examples" / "support-baseline.json")

    first = run_simulation(model)
    repeated = run_simulation(model)

    assert first.model_dump(mode="json", by_alias=True) == repeated.model_dump(
        mode="json", by_alias=True
    )
    assert first.run.seed == 42
    assert first.system_metrics.created_items == 8
    assert first.system_metrics.completed_items == 8
    assert first.system_metrics.terminally_failed_items == 0
    assert first.system_metrics.total_rework_count == 2
    assert first.system_metrics.event_count == 164
    assert [metric.total_requests for metric in first.resource_pool_metrics] == [14, 10]
