from collections import Counter
from dataclasses import dataclass, field

from app.domain.models import EventType, OperationalModel, SimulationEvent

EventKey = tuple[str, str | None, int]


@dataclass
class AuditLedger:
    """Compact canonical evidence updated as events are emitted."""

    model: OperationalModel
    total_event_count: int = 0
    last_event_time: float | None = None
    last_sequence: int | None = None
    sequence_valid: bool = True
    time_valid: bool = True
    references_valid: bool = True
    routes_valid: bool = True
    capacity_valid: bool = True
    nonnegative_usage_valid: bool = True
    referenced_item_ids: set[str] = field(default_factory=set)
    created_counts: Counter[str] = field(default_factory=Counter)
    completion_counts: Counter[str] = field(default_factory=Counter)
    terminal_failure_counts: Counter[str] = field(default_factory=Counter)
    request_counts: Counter[EventKey] = field(default_factory=Counter)
    release_counts: Counter[EventKey] = field(default_factory=Counter)
    process_start_counts: Counter[EventKey] = field(default_factory=Counter)
    process_completion_counts: Counter[EventKey] = field(default_factory=Counter)
    route_selection_counts: Counter[str] = field(default_factory=Counter)
    rework_event_count: int = 0
    current_resource_usage: dict[str, int] = field(init=False)
    maximum_resource_usage: dict[str, int] = field(init=False)
    active_resources: Counter[EventKey] = field(default_factory=Counter)

    def __post_init__(self) -> None:
        self.current_resource_usage = {pool.id: 0 for pool in self.model.resource_pools}
        self.maximum_resource_usage = {pool.id: 0 for pool in self.model.resource_pools}

    def record(self, event: SimulationEvent) -> None:
        expected_sequence = self.total_event_count
        if event.sequence != expected_sequence:
            self.sequence_valid = False
        if self.last_sequence is not None and event.sequence <= self.last_sequence:
            self.sequence_valid = False
        if self.last_event_time is not None and event.simulation_time < self.last_event_time:
            self.time_valid = False
        self.last_sequence = event.sequence
        self.last_event_time = event.simulation_time
        self.total_event_count += 1
        self.referenced_item_ids.add(event.item_id)

        source_ids = {source.id for source in self.model.sources}
        stage_ids = {stage.id for stage in self.model.stages}
        route_by_id = {route.id: route for route in self.model.routes}
        pool_by_id = {pool.id: pool for pool in self.model.resource_pools}
        if (
            (event.source_id is not None and event.source_id not in source_ids)
            or (event.stage_id is not None and event.stage_id not in stage_ids)
            or (event.route_id is not None and event.route_id not in route_by_id)
            or (
                event.resource_pool_id is not None
                and event.resource_pool_id not in pool_by_id
            )
        ):
            self.references_valid = False

        key = (event.item_id, event.stage_id, event.attempt or 0)
        if event.event_type is EventType.ITEM_CREATED:
            self.created_counts[event.item_id] += 1
        elif event.event_type is EventType.ITEM_COMPLETED:
            self.completion_counts[event.item_id] += 1
        elif (
            event.event_type is EventType.ITEM_FAILED
            and event.reason == "maximum_rework_attempts_exceeded"
        ):
            self.terminal_failure_counts[event.item_id] += 1
        elif event.event_type is EventType.RESOURCE_REQUESTED:
            self.request_counts[key] += 1
        elif event.event_type is EventType.RESOURCE_RELEASED:
            self.release_counts[key] += 1
            if event.resource_pool_id in self.current_resource_usage:
                self.current_resource_usage[event.resource_pool_id] -= 1
                self.active_resources[key] -= 1
                if (
                    self.current_resource_usage[event.resource_pool_id] < 0
                    or self.active_resources[key] < 0
                ):
                    self.nonnegative_usage_valid = False
        elif event.event_type is EventType.PROCESS_STARTED:
            self.process_start_counts[key] += 1
            if event.resource_pool_id in self.current_resource_usage:
                pool_id = event.resource_pool_id
                self.current_resource_usage[pool_id] += 1
                self.active_resources[key] += 1
                self.maximum_resource_usage[pool_id] = max(
                    self.maximum_resource_usage[pool_id],
                    self.current_resource_usage[pool_id],
                )
                if self.current_resource_usage[pool_id] > pool_by_id[pool_id].capacity:
                    self.capacity_valid = False
        elif event.event_type is EventType.PROCESS_COMPLETED:
            self.process_completion_counts[key] += 1
        elif event.event_type is EventType.ITEM_REWORKED:
            self.rework_event_count += 1

        if event.event_type is EventType.ROUTE_SELECTED:
            if event.route_id is None or event.route_id not in route_by_id:
                self.routes_valid = False
            else:
                route = route_by_id[event.route_id]
                valid_targets = {option.target_id for option in route.options}
                if event.stage_id != route.from_stage_id or event.target_id not in valid_targets:
                    self.routes_valid = False
                self.route_selection_counts[event.route_id] += 1

    @classmethod
    def from_events(
        cls, model: OperationalModel, events: list[SimulationEvent]
    ) -> "AuditLedger":
        ledger = cls(model)
        for event in events:
            ledger.record(event)
        return ledger
