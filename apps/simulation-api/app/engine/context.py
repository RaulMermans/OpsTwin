import random
from dataclasses import dataclass

import simpy

from app.domain.models import (
    ItemLifecycle,
    ObservationConfig,
    OperationalModel,
    ResultDetailConfig,
)
from app.engine.audit import AuditLedger
from app.engine.events import EventRecorder
from app.engine.observation import ObservationCollector


@dataclass
class ResourceEvidence:
    busy_time: float = 0
    current_usage: int = 0
    maximum_concurrent_usage: int = 0
    total_requests: int = 0


class SimulationContext:
    """Own all mutable state for exactly one simulation run."""

    def __init__(
        self,
        model: OperationalModel,
        seed: int,
        observation: ObservationConfig,
        result_detail: ResultDetailConfig,
        selected_item_ids: list[str],
    ) -> None:
        self.environment = simpy.Environment()
        self.random_generator = random.Random(seed)
        self.model = model
        self.audit_ledger = AuditLedger(model)
        self.observation_collector = ObservationCollector(model, observation)
        self.event_recorder = EventRecorder(
            self.audit_ledger,
            self.observation_collector,
            result_detail.mode,
            set(selected_item_ids),
        )
        self.item_states: list[ItemLifecycle] = []
        self.resource_registry = {
            pool.id: simpy.PriorityResource(self.environment, capacity=pool.capacity)
            for pool in model.resource_pools
        }
        self.resource_evidence = {pool.id: ResourceEvidence() for pool in model.resource_pools}
        self.stage_maximum_queues = {stage.id: 0 for stage in model.stages}
        self.stage_waiting = {stage.id: 0 for stage in model.stages}
