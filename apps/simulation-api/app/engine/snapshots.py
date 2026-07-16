from dataclasses import dataclass

from app.domain.models import SimulationResult


@dataclass(frozen=True)
class MetricSnapshot:
    run_index: int
    seed: int
    system: dict[str, float]
    stages: dict[str, dict[str, float]]
    resources: dict[str, dict[str, float]]

    @property
    def representative_vector(self) -> dict[str, float]:
        return {
            "slaAttainment": self.system["slaAttainment"],
            "averageCycleTime": self.system["averageCycleTime"],
            "p95CycleTime": self.system["p95CycleTime"],
            "timeWeightedWip": self.system["timeWeightedWip"],
            "totalReworkCount": self.system["totalReworkCount"],
        }


def extract_metric_snapshot(run_index: int, result: SimulationResult) -> MetricSnapshot:
    system = result.system_metrics
    return MetricSnapshot(
        run_index=run_index,
        seed=result.run.seed,
        system={
            "averageWaitingTime": system.average_waiting_time,
            "averageProcessingTime": system.average_processing_time,
            "averageCycleTime": system.average_cycle_time,
            "p95CycleTime": system.p95_cycle_time,
            "slaAttainment": system.sla_attainment,
            "completionRate": system.completion_rate,
            "terminalFailureRate": system.failure_rate,
            "flowEfficiency": system.flow_efficiency,
            "timeWeightedWip": system.time_weighted_wip,
            "timeWeightedQueueLength": system.time_weighted_queue_length,
            "totalReworkCount": float(system.total_rework_count),
            "completedItems": float(system.completed_items),
            "terminallyFailedItems": float(system.terminally_failed_items),
            "eventCount": float(system.event_count),
        },
        stages={
            stage.stage_id: {
                "averageWaitingTime": stage.average_waiting_time,
                "averageProcessingTime": stage.average_processing_time,
                "timeWeightedQueueLength": stage.time_weighted_queue_length,
                "failureRate": (
                    stage.failure_count / stage.visit_count if stage.visit_count else 0.0
                ),
                "reworkCount": float(stage.rework_count),
                "visitCount": float(stage.visit_count),
            }
            for stage in result.stage_metrics
        },
        resources={
            resource.resource_pool_id: {
                "utilization": resource.utilization,
                "idleProportion": resource.idle_capacity_proportion,
                "meanRequestWait": resource.mean_request_wait,
                "maximumConcurrentUsage": float(resource.maximum_concurrent_usage),
                "requestCount": float(resource.total_requests),
            }
            for resource in result.resource_pool_metrics
        },
    )
