import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


def test_golden_operational_snapshot_matches_os_1_0_0(repository_root: Path) -> None:
    schema = json.loads(
        (repository_root / "contracts" / "operational-snapshot.schema.json").read_text(
            encoding="utf-8"
        )
    )
    example = json.loads(
        (
            repository_root
            / "contracts"
            / "examples"
            / "operational-snapshot-golden.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(example)
    assert example["schemaVersion"] == "os.1.0.0"
    assert example["provenance"]["evidenceClass"] == "synthetic"
    assert "baselineModel" not in example


def test_unsupported_snapshot_schema_version_is_rejected(repository_root: Path) -> None:
    schema = json.loads(
        (repository_root / "contracts" / "operational-snapshot.schema.json").read_text(
            encoding="utf-8"
        )
    )
    example = json.loads(
        (
            repository_root
            / "contracts"
            / "examples"
            / "operational-snapshot-golden.json"
        ).read_text(encoding="utf-8")
    )
    example["schemaVersion"] = "0.2.0"
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(example)
