from __future__ import annotations

from app.calibration.catalog import request_for_fixture
from app.calibration.construct import model_fingerprint
from app.calibration.histories import generate_history
from app.calibration.snapshot import parse_utc, sha256_canonical
from app.calibration.workflow import _content_identity, _execution_identity, calibrate


def test_returned_model_fingerprint_matches_recomputation() -> None:
    snapshot = generate_history("golden", 71)
    request = request_for_fixture("cg3-golden-analytical", snapshot, approve=True)
    artifact = calibrate(snapshot, request)
    assert artifact.constructed_model is not None
    assert artifact.model_fingerprint == model_fingerprint(artifact.constructed_model)
    assert artifact.constructed_model.sources[0].item_count == 1
    assert artifact.validation_configuration["itemCount"] >= 1
    assert artifact.execution_identity
    assert artifact.execution_identity != artifact.model_fingerprint
    train_start = parse_utc(artifact.training_configuration["start"])
    train_end = parse_utc(artifact.training_configuration["end"])
    hold_start = parse_utc(artifact.validation_configuration["start"])
    hold_end = parse_utc(artifact.validation_configuration["end"])
    assert train_start and train_end and hold_start and hold_end
    recomputed = _execution_identity(
        artifact.model_fingerprint or "",
        train_start,
        train_end,
        hold_start,
        hold_end,
        artifact.execution_metadata.simulation_seeds,
        artifact.execution_metadata.item_count,
        request,
    )
    assert artifact.execution_identity == recomputed
    assert artifact.content_identity == _content_identity(request, artifact.model_fingerprint)
    assert sha256_canonical({"x": 1.0}) == sha256_canonical({"x": 1})
