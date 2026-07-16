import random

from app.domain.models import (
    ExponentialDistribution,
    FixedDistribution,
    ProcessingDistribution,
    TriangularDistribution,
    UniformDistribution,
)


def sample_distribution(
    distribution: ProcessingDistribution | object, generator: random.Random
) -> float:
    """Sample a supported processing duration from the run-local generator."""
    if isinstance(distribution, FixedDistribution):
        return distribution.value
    if isinstance(distribution, ExponentialDistribution):
        return generator.expovariate(1 / distribution.mean)
    if isinstance(distribution, UniformDistribution):
        return generator.uniform(distribution.minimum, distribution.maximum)
    if isinstance(distribution, TriangularDistribution):
        return generator.triangular(distribution.minimum, distribution.maximum, distribution.mode)
    raise TypeError(f"unsupported distribution: {type(distribution).__name__}")
