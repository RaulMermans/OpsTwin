from app.sensitivity_benchmark import benchmark_case


def test_gm098_sensitivity_benchmark_smoke_reports_bounded_retention() -> None:
    result = benchmark_case(item_count=10, run_count=2, value_count=2)

    assert result["estimatedWorkUnits"] == 40
    assert result["ordinarySimulationExecutions"] == 4
    assert result["minimumPairedRunRatioObserved"] == 1
    assert result["returnedEventCount"] == 0
    assert result["integrity"] == "passed"
    assert result["payloadBytes"] > 0
