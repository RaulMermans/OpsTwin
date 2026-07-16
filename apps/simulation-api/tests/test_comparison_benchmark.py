from app.comparison_benchmark import benchmark_case


def test_gm041_comparison_benchmark_smoke_reports_bounded_retention() -> None:
    result = benchmark_case(item_count=10, run_count=2, scenario_count=1, sample_limit=2)

    assert result["itemsPerRun"] == 10
    assert result["runCount"] == 2
    assert result["scenarioCount"] == 1
    assert result["totalModelVariants"] == 2
    assert result["estimatedWorkUnits"] == 40
    assert result["ordinarySimulationExecutions"] == 4
    assert result["representativeReruns"] == 2
    assert result["successfulScenarios"] == 1
    assert result["failedScenarios"] == 0
    assert result["minimumPairedRunRatioObserved"] == 1
    assert result["maximumSimultaneouslyRetainedEventRichResults"] == 2
    assert result["returnedEventCount"] == 32
    assert result["integrity"] == "passed"
    assert result["executionSeconds"] >= 0
    assert result["meanSimulationExecutionSeconds"] >= 0
    assert result["aggregateComparisonPayloadBytes"] > 0
    assert result["baselineRepresentativePayloadBytes"] > 0
    assert result["scenarioRepresentativePayloadBytes"] > 0
