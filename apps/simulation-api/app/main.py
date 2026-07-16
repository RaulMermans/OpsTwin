from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.comparison import ScenarioComparisonRequest, ScenarioComparisonResult
from app.domain.economics import (
    EconomicComparisonRequest,
    EconomicComparisonResult,
    EconomicSensitivityRequest,
    EconomicSensitivityResult,
)
from app.domain.models import HealthResponse, SimulationRequest, SimulationResult
from app.domain.repeated import RepeatedSimulationRequest, RepeatedSimulationResult
from app.domain.sensitivity import SensitivityRequest, SensitivityResult
from app.economics.comparison import run_economic_comparison
from app.economics.sensitivity import run_economic_sensitivity
from app.engine.integrity import SimulationIntegrityError
from app.engine.repeated import RepeatedSimulationError, run_repeated_simulation
from app.engine.simulator import run_simulation
from app.scenarios.coordinator import (
    ComparisonWorkBudgetError,
    ScenarioComparisonError,
    run_scenario_comparison,
)
from app.sensitivity.coordinator import (
    SensitivityAnalysisError,
    SensitivityWorkBudgetError,
    run_sensitivity_analysis,
)
from app.sensitivity.materializer import SensitivityPreparationError

API_PREFIX = "/api/simulation"
app = FastAPI(title="OpsTwin Simulation API", version="0.7.0")
router = APIRouter(prefix=API_PREFIX)


def _error_response(
    status_code: int,
    code: str,
    message: str,
    *,
    field_errors: list[dict[str, str]] | None = None,
    details: dict[str, int | float | str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "fieldErrors": field_errors or [],
                "details": details or {},
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error(
    _request: Request, error: RequestValidationError
) -> JSONResponse:
    validation_errors = error.errors()
    model_error = any(
        len(item["loc"]) > 2 and item["loc"][1] in {"model", "baselineModel"}
        for item in validation_errors
    )
    fields = [
        {
            "field": ".".join(str(segment) for segment in item["loc"] if segment != "body"),
            "message": str(item["msg"]),
        }
        for item in validation_errors
    ]
    return _error_response(
        422,
        "MODEL_VALIDATION_FAILED" if model_error else "REQUEST_VALIDATION_FAILED",
        (
            "Check the baseline assumptions."
            if model_error
            else "Check the highlighted request fields."
        ),
        field_errors=fields,
    )


@app.exception_handler(Exception)
async def unexpected_error(_request: Request, _error: Exception) -> JSONResponse:
    return _error_response(
        500,
        "INTERNAL_ERROR",
        "The service encountered an unexpected error.",
    )


def health() -> HealthResponse:
    """Report process health for the stateless simulation service."""
    return HealthResponse(status="ok", service="opstwin-simulation-api")


@app.get("/health", response_model=HealthResponse, include_in_schema=False)
def compatibility_health() -> HealthResponse:
    """Retain a documented root health alias for local infrastructure probes."""
    return health()


@router.get("/health", response_model=HealthResponse)
def simulation_health() -> HealthResponse:
    return health()


@router.post("/simulate", response_model=SimulationResult)
def simulate(request: SimulationRequest) -> SimulationResult | JSONResponse:
    """Run one stateless synchronous seeded simulation."""
    try:
        return run_simulation(
            request.model,
            seed_override=request.seed_override,
            run_label=request.run_label,
            observation=request.observation,
            result_detail=request.result_detail,
        )
    except SimulationIntegrityError:
        return _error_response(
            500,
            "SIMULATION_INTEGRITY_FAILED",
            "The simulation evidence failed its integrity checks.",
        )


@router.post("/simulate/repeated", response_model=RepeatedSimulationResult)
def simulate_repeated(
    request: RepeatedSimulationRequest,
) -> RepeatedSimulationResult | JSONResponse:
    """Run one stateless synchronous sequential repeated simulation."""
    try:
        return run_repeated_simulation(request)
    except RepeatedSimulationError:
        return _error_response(
            500,
            "REPEATED_SIMULATION_FAILED",
            "The repeated simulation could not produce sufficient evidence.",
        )


COMPARISON_ERROR_MESSAGES: dict[str, tuple[str, str]] = {
    "baseline_execution_failed": (
        "BASELINE_EXECUTION_FAILED",
        "The baseline simulation could not be completed.",
    ),
    "comparison_integrity_failed": (
        "COMPARISON_INTEGRITY_FAILED",
        "The comparison evidence failed its integrity checks.",
    ),
    "ordinary_run_retention": (
        "COMPARISON_INTEGRITY_FAILED",
        "The comparison evidence failed its integrity checks.",
    ),
}


@router.post("/compare/scenarios", response_model=ScenarioComparisonResult)
def compare_scenarios(
    request: ScenarioComparisonRequest,
) -> ScenarioComparisonResult | JSONResponse:
    """Compare a baseline and bounded scenarios across paired deterministic seeds."""
    try:
        return run_scenario_comparison(request)
    except ComparisonWorkBudgetError as error:
        return _error_response(
            422,
            "WORK_BUDGET_EXCEEDED",
            "This comparison is too large for synchronous execution.",
            details={
                "estimatedWorkUnits": error.estimated_work_units,
                "maximumWorkUnits": error.maximum_work_units,
            },
        )
    except ScenarioComparisonError as error:
        code, message = COMPARISON_ERROR_MESSAGES.get(
            error.code,
            ("COMPARISON_FAILED", "The comparison could not be completed."),
        )
        return _error_response(500, code, message)


@router.post("/analyze/sensitivity", response_model=SensitivityResult)
def analyze_sensitivity(
    request: SensitivityRequest,
) -> SensitivityResult | JSONResponse:
    """Run a bounded deterministic one-factor-at-a-time sensitivity analysis."""
    try:
        return run_sensitivity_analysis(request)
    except SensitivityWorkBudgetError as error:
        return _error_response(
            422,
            "WORK_BUDGET_EXCEEDED",
            "This sensitivity analysis is too large for synchronous execution.",
            details={
                "estimatedWorkUnits": error.estimated_work_units,
                "maximumWorkUnits": error.maximum_work_units,
            },
        )
    except SensitivityPreparationError as error:
        return _error_response(
            422,
            "SENSITIVITY_VALIDATION_FAILED",
            "Check the sensitivity target and tested values.",
            details={"category": error.category},
        )
    except SensitivityAnalysisError:
        return _error_response(
            500,
            "SENSITIVITY_ANALYSIS_FAILED",
            "The sensitivity analysis could not be completed.",
        )


@router.post("/analyze/economics", response_model=EconomicComparisonResult)
def analyze_economics(
    request: EconomicComparisonRequest,
) -> EconomicComparisonResult | JSONResponse:
    """Attach explicit recurring-cost evidence to one paired scenario comparison."""
    try:
        return run_economic_comparison(request)
    except ComparisonWorkBudgetError as error:
        return _error_response(
            422,
            "WORK_BUDGET_EXCEEDED",
            "This economic comparison is too large for synchronous execution.",
            details={
                "estimatedWorkUnits": error.estimated_work_units,
                "maximumWorkUnits": error.maximum_work_units,
            },
        )
    except (ScenarioComparisonError, ValueError):
        return _error_response(
            500,
            "ECONOMIC_COMPARISON_FAILED",
            "The economic comparison could not be completed.",
        )


@router.post("/analyze/economic-sensitivity", response_model=EconomicSensitivityResult)
def analyze_economic_sensitivity(
    request: EconomicSensitivityRequest,
) -> EconomicSensitivityResult | JSONResponse:
    """Capture explicit recurring-cost evidence during one existing sensitivity sweep."""
    try:
        return run_economic_sensitivity(request)
    except SensitivityWorkBudgetError as error:
        return _error_response(
            422,
            "WORK_BUDGET_EXCEEDED",
            "This economic sensitivity analysis is too large for synchronous execution.",
            details={
                "estimatedWorkUnits": error.estimated_work_units,
                "maximumWorkUnits": error.maximum_work_units,
            },
        )
    except (SensitivityPreparationError, SensitivityAnalysisError, ValueError):
        return _error_response(
            500,
            "ECONOMIC_SENSITIVITY_FAILED",
            "The economic sensitivity analysis could not be completed.",
        )


app.include_router(router)
