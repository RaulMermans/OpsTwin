from dataclasses import dataclass

from app.domain.models import (
    EventType,
    ItemLifecycle,
    ObservationConfig,
    ObservationMetadata,
    OperationalModel,
    SimulationEvent,
)


@dataclass(frozen=True)
class ObservationEvidence:
    metadata: ObservationMetadata
    included_items: list[ItemLifecycle]
    wip_area: float
    stage_queue_areas: dict[str, float]
    stage_maximum_queues: dict[str, int]
    pool_busy_areas: dict[str, float]
    pool_maximum_usage: dict[str, int]
    pool_request_counts: dict[str, int]
    pool_request_waits: dict[str, list[float]]


class ObservationCollector:
    """Integrate exact step-state evidence without retaining event objects."""

    def __init__(self, model: OperationalModel, observation: ObservationConfig) -> None:
        self.model = model
        self.start = observation.warmup_duration
        self.configured_end = (
            self.start + observation.measurement_duration
            if observation.measurement_duration is not None
            else None
        )
        self.stage_queue = {stage.id: 0 for stage in model.stages}
        self.stage_queue_areas = {stage.id: 0.0 for stage in model.stages}
        self.stage_maximum_queues = {stage.id: 0 for stage in model.stages}
        self.pool_usage = {pool.id: 0 for pool in model.resource_pools}
        self.pool_busy_areas = {pool.id: 0.0 for pool in model.resource_pools}
        self.pool_maximum_usage = {pool.id: 0 for pool in model.resource_pools}
        self.pool_request_counts = {pool.id: 0 for pool in model.resource_pools}
        self.pool_request_waits: dict[str, list[float]] = {
            pool.id: [] for pool in model.resource_pools
        }
        self.pending_requests: dict[tuple[str, str, int], tuple[float, bool]] = {}
        self.wip = 0
        self.wip_area = 0.0
        self.last_time = 0.0

    def _integrate(self, until: float, end: float) -> None:
        overlap = max(0.0, min(until, end) - max(self.last_time, self.start))
        if overlap == 0:
            return
        self.wip_area += self.wip * overlap
        for stage_id, count in self.stage_queue.items():
            self.stage_queue_areas[stage_id] += count * overlap
            self.stage_maximum_queues[stage_id] = max(
                self.stage_maximum_queues[stage_id], count
            )
        for pool_id, count in self.pool_usage.items():
            self.pool_busy_areas[pool_id] += count * overlap
            self.pool_maximum_usage[pool_id] = max(
                self.pool_maximum_usage[pool_id], count
            )

    def record(self, event: SimulationEvent) -> None:
        end = self.configured_end if self.configured_end is not None else event.simulation_time
        self._integrate(event.simulation_time, end)
        self.last_time = event.simulation_time
        event_time = event.simulation_time

        if event.event_type is EventType.ITEM_CREATED:
            self.wip += 1
        elif event.event_type is EventType.ITEM_COMPLETED:
            self.wip -= 1
        elif (
            event.event_type is EventType.ITEM_FAILED
            and event.reason == "maximum_rework_attempts_exceeded"
        ):
            self.wip -= 1
        elif event.event_type is EventType.RESOURCE_REQUESTED:
            if event.resource_pool_id is not None and event.stage_id is not None:
                key = (event.item_id, event.stage_id, event.attempt or 0)
                was_waiting = event.reason == "waiting"
                self.pending_requests[key] = (event_time, was_waiting)
                if was_waiting:
                    self.stage_queue[event.stage_id] += 1
                measurement_end = self.configured_end
                if event_time >= self.start and (
                    measurement_end is None or event_time < measurement_end
                ):
                    self.pool_request_counts[event.resource_pool_id] += 1
        elif event.event_type is EventType.PROCESS_STARTED:
            if event.resource_pool_id is not None and event.stage_id is not None:
                self.pool_usage[event.resource_pool_id] += 1
                key = (event.item_id, event.stage_id, event.attempt or 0)
                request = self.pending_requests.pop(key, None)
                if request is not None:
                    requested_at, was_waiting = request
                    if was_waiting:
                        self.stage_queue[event.stage_id] -= 1
                    measurement_end = self.configured_end
                    if requested_at >= self.start and (
                        measurement_end is None or event_time <= measurement_end
                    ):
                        self.pool_request_waits[event.resource_pool_id].append(
                            event_time - requested_at
                        )
        elif event.event_type is EventType.RESOURCE_RELEASED and event.resource_pool_id is not None:
            self.pool_usage[event.resource_pool_id] -= 1

        measurement_end = self.configured_end
        if event_time >= self.start and (
            measurement_end is None or event_time < measurement_end
        ):
            for stage_id, count in self.stage_queue.items():
                self.stage_maximum_queues[stage_id] = max(
                    self.stage_maximum_queues[stage_id], count
                )
            for pool_id, count in self.pool_usage.items():
                self.pool_maximum_usage[pool_id] = max(
                    self.pool_maximum_usage[pool_id], count
                )

    def finalize(
        self, items: list[ItemLifecycle], simulation_end: float
    ) -> ObservationEvidence:
        end = self.configured_end if self.configured_end is not None else simulation_end
        if end < self.start:
            raise ValueError("warmupDuration exceeds the inferred simulation horizon")
        self._integrate(end, end)

        def terminal_time(item: ItemLifecycle) -> float | None:
            return item.completed_at if item.completed else item.terminal_failure_at

        created_during = [item for item in items if self.start <= item.created_at < end]
        included = [
            item
            for item in created_during
            if terminal_time(item) is not None and terminal_time(item) <= end  # type: ignore[operator]
        ]
        completed_during = [
            item
            for item in items
            if item.completed_at is not None and self.start <= item.completed_at <= end
        ]
        failed_during = [
            item
            for item in items
            if item.terminal_failure_at is not None
            and self.start <= item.terminal_failure_at <= end
        ]
        active_at_end = [
            item
            for item in items
            if item.created_at < end
            and (terminal_time(item) is None or terminal_time(item) > end)  # type: ignore[operator]
        ]
        incomplete_at_end = [
            item
            for item in created_during
            if terminal_time(item) is None or terminal_time(item) > end  # type: ignore[operator]
        ]
        return ObservationEvidence(
            metadata=ObservationMetadata(
                measurement_start=self.start,
                measurement_end=end,
                simulation_end=simulation_end,
                measurement_duration=end - self.start,
                created_during_window=len(created_during),
                completed_during_window=len(completed_during),
                terminally_failed_during_window=len(failed_during),
                active_at_measurement_end=len(active_at_end),
                excluded_pre_warmup_items=sum(
                    item.created_at < self.start for item in items
                ),
                incomplete_at_measurement_end=len(incomplete_at_end),
            ),
            included_items=included,
            wip_area=self.wip_area,
            stage_queue_areas=self.stage_queue_areas,
            stage_maximum_queues=self.stage_maximum_queues,
            pool_busy_areas=self.pool_busy_areas,
            pool_maximum_usage=self.pool_maximum_usage,
            pool_request_counts=self.pool_request_counts,
            pool_request_waits=self.pool_request_waits,
        )


def build_observation_evidence(
    model: OperationalModel,
    items: list[ItemLifecycle],
    events: list[SimulationEvent],
    observation: ObservationConfig,
    simulation_end: float,
) -> ObservationEvidence:
    """Build evidence from supplied events for direct validation tests."""
    collector = ObservationCollector(model, observation)
    for event in events:
        collector.record(event)
    return collector.finalize(items, simulation_end)
