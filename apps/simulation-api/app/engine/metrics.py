from math import ceil

from app.domain.models import OperationalModel, ResourcePoolMetrics, StageMetrics, SystemMetrics
from app.engine.observation import ObservationEvidence


def calculate_system_metrics(
    model: OperationalModel,
    observation: ObservationEvidence,
    event_count: int,
) -> SystemMetrics:
    """Calculate windowed logical-item and time-weighted system metrics."""
    items = observation.included_items
    completed = [item for item in items if item.completed]
    failed = [item for item in items if item.terminally_failed]
    terminal_count = len(completed) + len(failed)
    cycles = sorted(item.cycle_time for item in completed)
    p95 = cycles[ceil(0.95 * len(cycles)) - 1] if cycles else 0
    attained = 0
    for item in completed:
        target = next(
            (
                rule.target_duration
                for rule in model.sla_rules
                if rule.source_id in (None, item.source_id)
            ),
            model.sla_rules[0].target_duration,
        )
        attained += item.cycle_time <= target
    duration = observation.metadata.measurement_duration
    total_waiting = sum(item.waiting_time for item in items)
    total_processing = sum(item.processing_time for item in items)
    total_cycle = sum(item.cycle_time for item in items)
    completion_rate = (
        observation.metadata.completed_during_window / duration if duration else 0
    )
    return SystemMetrics(
        created_items=observation.metadata.created_during_window,
        completed_items=observation.metadata.completed_during_window,
        terminally_failed_items=observation.metadata.terminally_failed_during_window,
        throughput=completion_rate,
        average_waiting_time=total_waiting / terminal_count if terminal_count else 0,
        average_processing_time=total_processing / terminal_count if terminal_count else 0,
        average_cycle_time=(
            sum(item.cycle_time for item in completed) / len(completed) if completed else 0
        ),
        p95_cycle_time=p95,
        maximum_queue_length=max(observation.stage_maximum_queues.values(), default=0),
        sla_attainment=attained / terminal_count if terminal_count else 0,
        total_rework_count=sum(item.rework_count for item in items),
        event_count=event_count,
        arrival_rate=(observation.metadata.created_during_window / duration if duration else 0),
        completion_rate=completion_rate,
        failure_rate=(
            observation.metadata.terminally_failed_during_window / duration if duration else 0
        ),
        time_weighted_wip=observation.wip_area / duration if duration else 0,
        time_weighted_queue_length=(
            sum(observation.stage_queue_areas.values()) / duration if duration else 0
        ),
        flow_efficiency=total_processing / total_cycle if total_cycle else 0,
    )


def calculate_stage_metrics(
    model: OperationalModel,
    observation: ObservationEvidence,
) -> list[StageMetrics]:
    """Calculate visit and time-weighted stage metrics in model order."""
    result: list[StageMetrics] = []
    all_visits = [visit for item in observation.included_items for visit in item.visits]
    total_waiting = sum(visit.waiting_time for visit in all_visits)
    total_processing = sum(visit.processing_time for visit in all_visits)
    duration = observation.metadata.measurement_duration
    for stage in model.stages:
        visits = [visit for visit in all_visits if visit.stage_id == stage.id]
        count = len(visits)
        stage_waiting = sum(visit.waiting_time for visit in visits)
        stage_processing = sum(visit.processing_time for visit in visits)
        result.append(
            StageMetrics(
                stage_id=stage.id,
                visit_count=count,
                completed_processing_count=count,
                average_waiting_time=stage_waiting / count if count else 0,
                average_processing_time=stage_processing / count if count else 0,
                failure_count=sum(visit.failed for visit in visits),
                rework_count=sum(visit.reworked for visit in visits),
                maximum_queue_length=observation.stage_maximum_queues[stage.id],
                time_weighted_queue_length=(
                    observation.stage_queue_areas[stage.id] / duration if duration else 0
                ),
                waiting_time_share=stage_waiting / total_waiting if total_waiting else 0,
                processing_time_share=(
                    stage_processing / total_processing if total_processing else 0
                ),
            )
        )
    return result


def calculate_resource_metrics(
    model: OperationalModel,
    observation: ObservationEvidence,
) -> list[ResourcePoolMetrics]:
    """Calculate clipped busy-capacity metrics once per shared resource pool."""
    result: list[ResourcePoolMetrics] = []
    duration = observation.metadata.measurement_duration
    for pool in model.resource_pools:
        busy_area = observation.pool_busy_areas[pool.id]
        capacity_time = pool.capacity * duration
        utilization = busy_area / capacity_time if capacity_time else 0
        waits = observation.pool_request_waits[pool.id]
        result.append(
            ResourcePoolMetrics(
                resource_pool_id=pool.id,
                capacity=pool.capacity,
                busy_time=busy_area,
                utilization=utilization,
                maximum_concurrent_usage=observation.pool_maximum_usage[pool.id],
                total_requests=observation.pool_request_counts[pool.id],
                busy_capacity_time=busy_area,
                available_capacity_time=capacity_time - busy_area,
                idle_capacity_proportion=1 - utilization if capacity_time else 0,
                mean_request_wait=sum(waits) / len(waits) if waits else 0,
            )
        )
    return result
