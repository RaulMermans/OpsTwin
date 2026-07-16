import random

from app.domain.models import RouteConfig, RouteOption


def select_route_option(route: RouteConfig, generator: random.Random) -> RouteOption:
    """Select exactly one option in contract order using run-local randomness."""
    if len(route.options) == 1:
        return route.options[0]
    sample = generator.random()
    cumulative = 0.0
    for option in route.options:
        cumulative += option.probability
        if sample < cumulative:
            return option
    return route.options[-1]
