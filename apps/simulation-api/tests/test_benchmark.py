import json

import pytest

from app import benchmark


def test_benchmark_case_reports_reconciled_smoke_metrics() -> None:
    result = benchmark.benchmark_case(100, "summary")

    assert result["model"] == "Performance baseline"
    assert result["seed"] == 20250715
    assert result["itemCount"] == 100
    assert result["stageCount"] == 1
    assert result["eventCount"] == 800
    assert result["includedEventCount"] == 0
    assert result["payloadBytes"] > 0
    assert result["executionSeconds"] >= 0
    assert result["serializationSeconds"] >= 0
    assert result["integrity"] == "passed"


def test_smoke_main_prints_valid_json(capsys: pytest.CaptureFixture[str]) -> None:
    benchmark.main(["--smoke"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert len(payload["results"]) == 1
    assert payload["results"][0]["itemCount"] == 100
