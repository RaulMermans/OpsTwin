from typing import Any

from app.domain.models import OperationalModel


def single_stage_model(
    *,
    item_count: int,
    arrival: dict[str, Any],
    processing: dict[str, Any],
    seed: int = 20250715,
    failure: dict[str, Any] | None = None,
) -> OperationalModel:
    stage: dict[str, Any] = {
        "id": "service",
        "name": "Service",
        "resourcePoolId": "server",
        "processingTime": processing,
        "queuePolicy": "fifo",
    }
    routes: list[dict[str, Any]] = [
        {
            "id": "service-complete",
            "kind": "success",
            "fromStageId": "service",
            "options": [{"targetType": "completion", "probability": 1}],
        }
    ]
    if failure is not None:
        stage["failure"] = failure
        routes.append(
            {
                "id": failure["routeId"],
                "kind": "failure",
                "fromStageId": "service",
                "options": [
                    {"targetType": "stage", "targetId": "service", "probability": 1}
                ],
            }
        )
    return OperationalModel.model_validate(
        {
            "schemaVersion": "0.2.0",
            "name": "Analytical single-server fixture",
            "timeUnit": "minutes",
            "runConfig": {"seed": seed},
            "sources": [
                {
                    "id": "jobs",
                    "name": "Jobs",
                    "itemCount": item_count,
                    "initialArrivalTime": 0,
                    "priority": 0,
                    "firstStageId": "service",
                    "arrival": arrival,
                }
            ],
            "resourcePools": [{"id": "server", "name": "Server", "capacity": 1}],
            "stages": [stage],
            "routes": routes,
            "slaRules": [{"id": "default", "targetDuration": 100}],
        }
    )


def mm1_theory(arrival_rate: float, service_rate: float) -> dict[str, float]:
    if arrival_rate >= service_rate:
        raise ValueError("M/M/1 benchmark requires arrival rate below service rate")
    utilization = arrival_rate / service_rate
    system_time = 1 / (service_rate - arrival_rate)
    queue_wait = arrival_rate / (service_rate * (service_rate - arrival_rate))
    return {
        "rho": utilization,
        "W": system_time,
        "Wq": queue_wait,
        "L": arrival_rate * system_time,
        "Lq": arrival_rate * queue_wait,
    }


def relative_error(actual: float, expected: float) -> float:
    return abs(actual - expected) / expected
