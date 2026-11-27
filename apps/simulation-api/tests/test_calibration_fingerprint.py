from __future__ import annotations

import json
from pathlib import Path

from app.calibration.snapshot import content_fingerprint


def test_canonical_fingerprint_cases(repository_root: Path) -> None:
    payload = json.loads(
        (repository_root / "contracts/examples/canonical-fingerprint/cases.json").read_text(
            encoding="utf-8"
        )
    )
    fingerprints = {name: content_fingerprint(item) for name, item in payload.items()}
    assert fingerprints["nested_a"] == fingerprints["nested_b"]
    assert fingerprints["volatile_a"] == fingerprints["volatile_b"]
    assert fingerprints["completeness_complete"] != fingerprints["completeness_partial"]
    assert fingerprints["origin_synthetic"] != fingerprints["origin_observed"]
    assert fingerprints["integer_and_float"] != fingerprints["unicode"]
    expected_path = repository_root / "contracts/examples/canonical-fingerprint/expected.json"
    if expected_path.exists():
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        assert fingerprints == expected
    else:
        expected_path.write_text(json.dumps(fingerprints, indent=2) + "\n", encoding="utf-8")
        raise AssertionError("wrote canonical fingerprint expected.json; re-run the test")


def test_bundled_schema_matches_contracts(repository_root: Path) -> None:
    bundled = (
        repository_root
        / "apps/simulation-api/app/calibration/data/operational-snapshot.schema.json"
    )
    canonical = repository_root / "contracts/operational-snapshot.schema.json"
    assert bundled.read_text(encoding="utf-8") == canonical.read_text(encoding="utf-8")
