import json
from pathlib import Path

from app.cli import main, run_sensitivity_request

FIXTURE = Path(__file__).parent / "fixtures" / "sensitivity-request.json"


def test_cli_request_runner_returns_06_result() -> None:
    result = run_sensitivity_request(FIXTURE)

    assert result["schemaVersion"] == "0.6.0"
    assert result["integrity"]["checksRun"] >= 18


def test_cli_sensitivity_prints_only_json(capsys: object) -> None:
    main(["sensitivity", str(FIXTURE)])
    captured = capsys.readouterr()  # type: ignore[attr-defined]

    assert json.loads(captured.out)["schemaVersion"] == "0.6.0"
    assert captured.err == ""
