from app.domain.models import ItemLifecycle, OperationalModel, SimulationEvent
from app.engine.audit import AuditLedger


class SimulationIntegrityError(RuntimeError):
    """Structured failure raised when canonical run evidence does not reconcile."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def validate_audit_ledger(
    model: OperationalModel,
    items: list[ItemLifecycle],
    ledger: AuditLedger,
) -> int:
    """Validate lifecycle invariants against compact canonical audit evidence."""
    checks_run = 0

    def require(condition: bool, code: str, message: str) -> None:
        if not condition:
            raise SimulationIntegrityError(code, message)

    item_ids = [item.item_id for item in items]
    item_id_set = set(item_ids)
    require(len(item_ids) == len(item_id_set), "duplicate_item", "duplicate logical item")
    checks_run += 1

    completed_items = [item for item in items if item.completed]
    failed_items = [item for item in items if item.terminally_failed]
    active_items = [item for item in items if not item.completed and not item.terminally_failed]
    require(
        len(items) == len(completed_items) + len(failed_items) + len(active_items),
        "lifecycle_totals",
        "lifecycle totals do not reconcile",
    )
    require(
        not any(item.completed and item.terminally_failed for item in items),
        "conflicting_terminal_state",
        "item cannot be completed and terminally failed",
    )
    checks_run += 1

    for item in items:
        require(
            ledger.completion_counts[item.item_id] == int(item.completed),
            "completion_count",
            "terminal event count does not match completed lifecycle",
        )
        require(
            ledger.terminal_failure_counts[item.item_id] == int(item.terminally_failed),
            "failure_count",
            "terminal event count does not match failed lifecycle",
        )
    checks_run += 1

    require(
        ledger.sequence_valid,
        "event_sequence",
        "event sequence values must be strictly increasing",
    )
    checks_run += 1
    require(
        ledger.time_valid,
        "event_time",
        "event timestamps must never decrease",
    )
    checks_run += 1

    require(
        set(ledger.created_counts) == item_id_set
        and all(count == 1 for count in ledger.created_counts.values()),
        "created_items",
        "every created item must have one logical lifecycle",
    )
    checks_run += 1
    require(
        ledger.referenced_item_ids == item_id_set,
        "unknown_item",
        "event references an unknown item",
    )
    checks_run += 1
    require(
        ledger.references_valid,
        "unknown_reference",
        "event references an unknown source, stage, route, or resource",
    )
    checks_run += 1
    require(
        ledger.routes_valid,
        "route_destination",
        "route selection points to an invalid destination",
    )
    checks_run += 1

    require(
        ledger.request_counts == ledger.release_counts,
        "request_release_pair",
        "resource acquisition must have a matching release",
    )
    checks_run += 1
    require(
        ledger.capacity_valid,
        "resource_capacity",
        "resource concurrent use exceeds capacity",
    )
    require(
        ledger.nonnegative_usage_valid,
        "resource_negative",
        "resource concurrent use cannot become negative",
    )
    require(
        all(value == 0 for value in ledger.current_resource_usage.values())
        and all(value == 0 for value in ledger.active_resources.values()),
        "resource_pair",
        "resource acquisition must have a matching release",
    )
    checks_run += 1

    require(
        ledger.process_start_counts == ledger.process_completion_counts,
        "process_pair",
        "every process start must have a matching process completion",
    )
    checks_run += 1
    require(
        sum(item.rework_count for item in items) == ledger.rework_event_count,
        "rework_count",
        "rework event count does not match lifecycle counts",
    )
    checks_run += 1
    require(
        sum(len(item.visits) for item in items) == sum(ledger.process_start_counts.values()),
        "visit_count",
        "stage visit counts do not match process starts",
    )
    checks_run += 1
    require(
        len(completed_items) == sum(ledger.completion_counts.values()),
        "completed_count",
        "completion counts do not match terminal events",
    )
    checks_run += 1
    require(
        all(item.cycle_time >= 0 for item in items)
        and all(visit.waiting_time >= 0 for item in items for visit in item.visits),
        "negative_duration",
        "cycle and queue waiting durations must be non-negative",
    )
    checks_run += 1
    return checks_run


def validate_simulation(
    model: OperationalModel,
    items: list[ItemLifecycle],
    events: list[SimulationEvent],
) -> int:
    """Validate supplied full events through the same compact ledger path."""
    return validate_audit_ledger(model, items, AuditLedger.from_events(model, events))
