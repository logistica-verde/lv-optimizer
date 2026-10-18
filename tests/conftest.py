import pytest

from app.optimization import route_optimizer


@pytest.fixture(autouse=True)
def fast_ga_parameters(monkeypatch):
    """The production GA budget takes seconds per run; tests use a smaller one."""
    monkeypatch.setattr(
        route_optimizer, "GA_PARAMETERS", dict(population_size=120, generations=300, mutation_rate=0.4)
    )
