import json
import sys
from pathlib import Path
from typing import Any

import pytest

from app import cli
from app.domain.models import ObservationConfig, ResultDetailConfig


def model_file(
    tmp_path: Path, deterministic_model_data: dict[str, Any]
) -> Path:
    path = tmp_path / "model.json"
    path.write_text(json.dumps(deterministic_model_data), encoding="utf-8")
    return path


def comparison_file(
    tmp_path: Path, deterministic_model_data: dict[str, Any]
) -> Path:
    path = tmp_path / "comparison.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": "0.5.0",
                "baselineModel": deterministic_model_data,
                "scenarios": [
                    {
                        "id": "capacity",
                        "name": "Capacity",
                        "overrides": [
                            {
                                "entityType": "resourcePool",
                                "entityId": "agents",
                                "field": "capacity",
                                "operation": "replace",
                                "value": 2,
                            }
                        ],
                    }
                ],
                "execution": {"baseSeed": 42, "runCount": 2},
                "objective": {
                    "metric": "averageCycleTime",
                    "direction": "minimize",
                },
                "representativeEvidence": {
                    "baseline": True,
                    "topRankedScenario": True,
                    "detailMode": "summary",
                    "sampledItemLimit": None,
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_cli_uses_typed_summary_result_by_default(
    tmp_path: Path, deterministic_model_data: dict[str, Any]
) -> None:
    result = cli.run_model(model_file(tmp_path, deterministic_model_data))

    assert result["schemaVersion"] == "0.3.0"
    assert result["run"]["modelName"] == "Deterministic Support Baseline"
    assert result["run"]["seed"] == 42
    assert result["systemMetrics"]["completedItems"] == 5
    assert result["resultDetail"]["mode"] == "summary"
    assert result["events"] == []


def test_cli_overrides_seed_observation_and_detail(
    tmp_path: Path, deterministic_model_data: dict[str, Any]
) -> None:
    result = cli.run_model(
        model_file(tmp_path, deterministic_model_data),
        seed_override=77,
        observation=ObservationConfig(warmup_duration=1, measurement_duration=20),
        result_detail=ResultDetailConfig(mode="sampled", sampled_item_limit=2),
    )

    assert result["run"]["seed"] == 77
    assert result["observation"]["measurementStart"] == 1
    assert result["observation"]["measurementEnd"] == 21
    assert result["resultDetail"]["mode"] == "sampled"
    assert len(result["resultDetail"]["selectedItemIds"]) == 2


def test_cli_main_prints_only_schema_valid_json(
    tmp_path: Path,
    deterministic_model_data: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = model_file(tmp_path, deterministic_model_data)

    cli.main([str(path), "--result-detail", "full"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["schemaVersion"] == "0.3.0"
    assert payload["resultDetail"]["mode"] == "full"
    assert captured.err == ""


def test_cli_invalid_detail_combination_exits_nonzero(
    tmp_path: Path,
    deterministic_model_data: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = model_file(tmp_path, deterministic_model_data)

    with pytest.raises(SystemExit) as error:
        cli.main(
            [
                str(path),
                "--result-detail",
                "summary",
                "--sampled-item-limit",
                "2",
            ]
        )

    assert error.value.code != 0
    assert capsys.readouterr().err


def test_repeated_cli_returns_typed_json(
    tmp_path: Path, deterministic_model_data: dict[str, Any]
) -> None:
    result = cli.run_repeated_model(
        model_file(tmp_path, deterministic_model_data),
        base_seed=42,
        run_count=2,
        representative_detail="summary",
    )

    assert result["schemaVersion"] == "0.4.0"
    assert result["successfulRunCount"] == 2
    assert result["representativeRun"]["detailMode"] == "summary"


def test_repeated_cli_main_prints_only_json(
    tmp_path: Path,
    deterministic_model_data: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = model_file(tmp_path, deterministic_model_data)

    cli.main(
        [
            "repeated",
            str(path),
            "--base-seed",
            "42",
            "--run-count",
            "2",
            "--representative-detail",
            "summary",
        ]
    )

    captured = capsys.readouterr()
    assert json.loads(captured.out)["schemaVersion"] == "0.4.0"
    assert captured.err == ""


def test_repeated_cli_invalid_combination_exits_nonzero(
    tmp_path: Path,
    deterministic_model_data: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = model_file(tmp_path, deterministic_model_data)

    with pytest.raises(SystemExit) as error:
        cli.main(
            [
                "repeated",
                str(path),
                "--base-seed",
                "42",
                "--run-count",
                "2",
                "--representative-detail",
                "full",
                "--sampled-item-limit",
                "2",
            ]
        )

    assert error.value.code != 0
    assert capsys.readouterr().err


def test_repeated_cli_uses_process_arguments(
    tmp_path: Path,
    deterministic_model_data: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = model_file(tmp_path, deterministic_model_data)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cli.py",
            "repeated",
            str(path),
            "--base-seed",
            "42",
            "--run-count",
            "2",
            "--representative-detail",
            "summary",
        ],
    )

    cli.main()

    assert json.loads(capsys.readouterr().out)["schemaVersion"] == "0.4.0"


def test_comparison_cli_prints_only_typed_json(
    tmp_path: Path,
    deterministic_model_data: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = comparison_file(tmp_path, deterministic_model_data)

    cli.main(["compare", str(path), "--run-count", "2"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["schemaVersion"] == "0.5.0"
    assert payload["requestedRunCount"] == 2
    assert captured.err == ""
