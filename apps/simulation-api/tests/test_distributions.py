import random

import pytest
from pydantic import ValidationError

from app.domain.models import (
    ExponentialDistribution,
    FixedDistribution,
    TriangularDistribution,
    UniformDistribution,
)
from app.engine.distributions import sample_distribution


def test_fixed_distribution_is_exact_and_does_not_advance_generator() -> None:
    generator = random.Random(123)
    before = generator.getstate()

    assert sample_distribution(FixedDistribution(type="fixed", value=8), generator) == 8
    assert generator.getstate() == before


@pytest.mark.parametrize(
    ("distribution", "expected"),
    [
        (UniformDistribution(type="uniform", minimum=5, maximum=10), 5.261817994254722),
        (ExponentialDistribution(type="exponential", mean=8), 0.43027514712234205),
        (
            TriangularDistribution(type="triangular", minimum=4, mode=7, maximum=12),
            5.121038078043143,
        ),
    ],
)
def test_seeded_distribution_sample_is_exact(distribution: object, expected: float) -> None:
    assert sample_distribution(distribution, random.Random(123)) == pytest.approx(
        expected, abs=1e-12
    )


@pytest.mark.parametrize(
    ("model", "values"),
    [
        (FixedDistribution, {"type": "fixed", "value": -1}),
        (ExponentialDistribution, {"type": "exponential", "mean": 0}),
        (UniformDistribution, {"type": "uniform", "minimum": 5, "maximum": 4}),
        (
            TriangularDistribution,
            {"type": "triangular", "minimum": 4, "mode": 13, "maximum": 12},
        ),
    ],
)
def test_invalid_distribution_parameters_are_rejected(
    model: object, values: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(values)  # type: ignore[attr-defined]


def test_same_seed_repeats_and_different_seed_varies() -> None:
    distribution = UniformDistribution(type="uniform", minimum=1, maximum=2)

    first = sample_distribution(distribution, random.Random(42))
    repeated = sample_distribution(distribution, random.Random(42))
    different = sample_distribution(distribution, random.Random(43))

    assert first == repeated
    assert different != first
