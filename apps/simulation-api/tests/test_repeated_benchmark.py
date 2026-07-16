from app.repeated_benchmark import benchmark_case


def test_gm029_repeated_benchmark_smoke_reports_retention() -> None:
    result = benchmark_case(item_count=10, run_count=2, sampled_item_limit=2)

    assert result["itemsPerRun"] == 10
    assert result["runCount"] == 2
    assert result["ordinaryRunCount"] == 2
    assert result["representativeRerunCount"] == 1
    assert result["successfulRuns"] == 2
    assert result["failedRuns"] == 0
    assert result["maximumSimultaneouslyRetainedFullResults"] == 1
    assert result["totalGeneratedEventCount"] == 240
    assert result["returnedEventCount"] == 16
    assert result["integrity"] == "passed"
    assert result["executionSeconds"] >= 0
    assert result["meanOrdinaryRunSeconds"] >= 0
    assert result["aggregatePayloadBytes"] > result["representativePayloadBytes"]
