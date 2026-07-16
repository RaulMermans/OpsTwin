import secrets
from collections.abc import Generator

import simpy

from app.domain.models import (
    EventType,
    FixedArrival,
    FixedDistribution,
    IntegrityStatus,
    ItemLifecycle,
    ObservationConfig,
    OperationalModel,
    PoissonArrival,
    ResultDetailConfig,
    RunMetadata,
    SimulationResult,
    StageVisit,
)
from app.engine.context import SimulationContext
from app.engine.distributions import sample_distribution
from app.engine.integrity import validate_audit_ledger
from app.engine.metrics import (
    calculate_resource_metrics,
    calculate_stage_metrics,
    calculate_system_metrics,
)
from app.engine.result_detail import build_result_detail_metadata, select_item_ids
from app.engine.routing import select_route_option


def run_simulation(
    model: OperationalModel,
    seed_override: int | None = None,
    run_label: str | None = None,
    observation: ObservationConfig | None = None,
    result_detail: ResultDetailConfig | None = None,
) -> SimulationResult:
    """Run a validated operational model with isolated state."""
    seed = seed_override if seed_override is not None else model.run_config.seed
    if seed is None:
        seed = secrets.randbits(63)
    observation_config = observation or ObservationConfig()
    detail_config = result_detail or ResultDetailConfig(mode="full")
    selected_item_ids = select_item_ids(model, seed, detail_config)
    context = SimulationContext(
        model,
        seed,
        observation_config,
        detail_config,
        selected_item_ids,
    )
    stage_by_id = {stage.id: stage for stage in model.stages}
    route_by_stage = {
        route.from_stage_id: route for route in model.routes if route.kind == "success"
    }
    route_by_id = {route.id: route for route in model.routes}

    def record(event_type: EventType, item: ItemLifecycle, **details: object) -> None:
        context.event_recorder.record(
            float(context.environment.now),
            event_type,
            item.item_id,
            source_id=item.source_id,
            priority=item.priority,
            **details,  # type: ignore[arg-type]
        )

    def process_item(
        item: ItemLifecycle, first_stage_id: str
    ) -> Generator[simpy.Event, object, None]:
        current_stage_id = first_stage_id
        while True:
            stage = stage_by_id[current_stage_id]
            pool = context.resource_registry[stage.resource_pool_id]
            evidence = context.resource_evidence[stage.resource_pool_id]
            visit_number = sum(visit.stage_id == stage.id for visit in item.visits) + 1
            queue_entered_at = float(context.environment.now)
            record(
                EventType.QUEUE_ENTERED,
                item,
                stage_id=stage.id,
                resource_pool_id=stage.resource_pool_id,
                attempt=visit_number,
            )
            request_priority = item.priority if stage.queue_policy == "priority" else 0
            with pool.request(priority=request_priority) as request:
                evidence.total_requests += 1
                was_waiting = not request.triggered
                record(
                    EventType.RESOURCE_REQUESTED,
                    item,
                    stage_id=stage.id,
                    resource_pool_id=stage.resource_pool_id,
                    attempt=visit_number,
                    reason="waiting" if was_waiting else "immediate",
                )
                if was_waiting:
                    context.stage_waiting[stage.id] += 1
                    context.stage_maximum_queues[stage.id] = max(
                        context.stage_maximum_queues[stage.id],
                        context.stage_waiting[stage.id],
                    )
                yield request
                if was_waiting:
                    context.stage_waiting[stage.id] -= 1
                evidence.current_usage += 1
                evidence.maximum_concurrent_usage = max(
                    evidence.maximum_concurrent_usage, evidence.current_usage
                )
                duration = sample_distribution(stage.processing_time, context.random_generator)
                process_started_at = float(context.environment.now)
                record(
                    EventType.PROCESS_STARTED,
                    item,
                    stage_id=stage.id,
                    resource_pool_id=stage.resource_pool_id,
                    attempt=visit_number,
                    sampled_duration=duration,
                )
                yield context.environment.timeout(duration)
                process_completed_at = float(context.environment.now)
                record(
                    EventType.PROCESS_COMPLETED,
                    item,
                    stage_id=stage.id,
                    resource_pool_id=stage.resource_pool_id,
                    attempt=visit_number,
                    sampled_duration=duration,
                )
                evidence.busy_time += duration
            evidence.current_usage -= 1
            record(
                EventType.RESOURCE_RELEASED,
                item,
                stage_id=stage.id,
                resource_pool_id=stage.resource_pool_id,
                attempt=visit_number,
            )

            failure = stage.failure
            failed = False
            if failure is not None:
                if failure.probability == 1:
                    failed = True
                elif failure.probability > 0:
                    failed = context.random_generator.random() < failure.probability
            if failed and failure is not None:
                accepted_rework = item.rework_count < failure.maximum_rework_attempts
                item.visits.append(
                    StageVisit(
                        item_id=item.item_id,
                        stage_id=stage.id,
                        resource_pool_id=stage.resource_pool_id,
                        visit_number=visit_number,
                        queue_entered_at=queue_entered_at,
                        process_started_at=process_started_at,
                        process_completed_at=process_completed_at,
                        sampled_duration=duration,
                        failed=True,
                        reworked=accepted_rework,
                    )
                )
                record(
                    EventType.ITEM_FAILED,
                    item,
                    stage_id=stage.id,
                    attempt=visit_number,
                    reason=(
                        "stage_failure" if accepted_rework else "maximum_rework_attempts_exceeded"
                    ),
                )
                if not accepted_rework:
                    item.terminally_failed = True
                    item.terminal_failure_at = float(context.environment.now)
                    return
                item.rework_count += 1
                failure_route = route_by_id[failure.route_id]
                failure_option = failure_route.options[0]
                record(
                    EventType.ROUTE_SELECTED,
                    item,
                    stage_id=stage.id,
                    route_id=failure_route.id,
                    target_id=failure_option.target_id,
                    attempt=visit_number,
                )
                record(
                    EventType.ITEM_REWORKED,
                    item,
                    stage_id=stage.id,
                    route_id=failure_route.id,
                    target_id=failure_option.target_id,
                    attempt=item.rework_count,
                )
                current_stage_id = failure_option.target_id or stage.id
                continue

            item.visits.append(
                StageVisit(
                    item_id=item.item_id,
                    stage_id=stage.id,
                    resource_pool_id=stage.resource_pool_id,
                    visit_number=visit_number,
                    queue_entered_at=queue_entered_at,
                    process_started_at=process_started_at,
                    process_completed_at=process_completed_at,
                    sampled_duration=duration,
                    failed=False,
                    reworked=False,
                )
            )
            route = route_by_stage[stage.id]
            option = select_route_option(route, context.random_generator)
            record(
                EventType.ROUTE_SELECTED,
                item,
                stage_id=stage.id,
                route_id=route.id,
                target_id=option.target_id,
                attempt=visit_number,
            )
            if option.target_type == "completion":
                item.completed = True
                item.completed_at = float(context.environment.now)
                record(EventType.ITEM_COMPLETED, item, stage_id=stage.id)
                return
            current_stage_id = option.target_id or stage.id

    def source_process(source_index: int) -> Generator[simpy.Event, object, None]:
        source = model.sources[source_index]
        yield context.environment.timeout(source.initial_arrival_time)
        for item_number in range(1, source.item_count + 1):
            item = ItemLifecycle(
                item_id=f"{source.id}-item-{item_number}",
                source_id=source.id,
                priority=source.priority,
                created_at=float(context.environment.now),
                visits=[],
            )
            context.item_states.append(item)
            record(EventType.ITEM_CREATED, item)
            context.environment.process(process_item(item, source.first_stage_id))
            if item_number < source.item_count:
                if isinstance(source.arrival, FixedArrival):
                    delay = source.arrival.interval
                elif isinstance(source.arrival, PoissonArrival):
                    delay = context.random_generator.expovariate(
                        1 / source.arrival.mean_interarrival_time
                    )
                else:
                    raise TypeError("unsupported arrival configuration")
                yield context.environment.timeout(delay)

    for source_index in range(len(model.sources)):
        context.environment.process(source_process(source_index))
    context.environment.run()
    duration = float(context.environment.now)
    retained_events = context.event_recorder.events
    integrity_checks = validate_audit_ledger(
        model, context.item_states, context.audit_ledger
    )
    observation_evidence = context.observation_collector.finalize(
        context.item_states, duration
    )
    deterministic = (
        all(isinstance(source.arrival, FixedArrival) for source in model.sources)
        and all(
            isinstance(stage.processing_time, FixedDistribution)
            and (stage.failure is None or stage.failure.probability in (0, 1))
            for stage in model.stages
        )
        and all(
            sum(option.probability > 0 for option in route.options) == 1 for route in model.routes
        )
    )
    detail_metadata = build_result_detail_metadata(
        retained_events,
        context.audit_ledger.total_event_count,
        selected_item_ids,
        detail_config,
    )
    return SimulationResult(
        run=RunMetadata(
            model_name=model.name,
            seed=seed,
            completed_at=duration,
            deterministic=deterministic,
            run_label=run_label,
        ),
        observation=observation_evidence.metadata,
        system_metrics=calculate_system_metrics(
            model, observation_evidence, context.audit_ledger.total_event_count
        ),
        stage_metrics=calculate_stage_metrics(model, observation_evidence),
        resource_pool_metrics=calculate_resource_metrics(model, observation_evidence),
        integrity=IntegrityStatus(checks_run=integrity_checks),
        result_detail=detail_metadata,
        events=retained_events,
        items=context.item_states,
    )
