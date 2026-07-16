from typing import Literal

from app.domain.models import EventType, SimulationEvent
from app.engine.audit import AuditLedger
from app.engine.observation import ObservationCollector


class EventRecorder:
    """Emit canonical evidence while retaining only requested event detail."""

    def __init__(
        self,
        ledger: AuditLedger,
        observation: ObservationCollector,
        mode: Literal["summary", "sampled", "full"],
        selected_item_ids: set[str],
    ) -> None:
        self.events: list[SimulationEvent] = []
        self.ledger = ledger
        self.observation = observation
        self.mode = mode
        self.selected_item_ids = selected_item_ids

    def record(
        self,
        simulation_time: float,
        event_type: EventType,
        item_id: str,
        **details: str | int | float | None,
    ) -> None:
        event = SimulationEvent.model_validate(
            {
                "simulation_time": simulation_time,
                "sequence": self.ledger.total_event_count,
                "event_type": event_type,
                "item_id": item_id,
                **details,
            }
        )
        self.ledger.record(event)
        self.observation.record(event)
        if self.mode == "full" or (
            self.mode == "sampled" and item_id in self.selected_item_ids
        ):
            self.events.append(event)
