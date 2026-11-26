import itertools

import numpy as np

from experiments.reference_heuristics import exact_optimum, nearest_neighbour, route_cost, two_opt


def asymmetric_costs(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    cost = rng.uniform(1.0, 10.0, (n, n))
    np.fill_diagonal(cost, 0.0)
    return cost


def brute_force(cost: np.ndarray) -> float:
    return min(route_cost(cost, [0, *order]) for order in itertools.permutations(range(1, len(cost))))


def test_nearest_neighbour_starts_at_the_depot_and_visits_every_point_once():
    route = nearest_neighbour(asymmetric_costs(8, 1))

    assert route[0] == 0
    assert sorted(route) == list(range(8))


def test_nearest_neighbour_always_takes_the_cheapest_next_leg():
    cost = np.array([[0, 5, 1, 9], [1, 0, 1, 1], [9, 2, 0, 3], [1, 1, 1, 0]], dtype=float)

    assert nearest_neighbour(cost) == [0, 2, 1, 3]


def test_two_opt_never_makes_the_route_worse_and_keeps_the_depot_first():
    for seed in range(20):
        cost = asymmetric_costs(9, seed)
        start = nearest_neighbour(cost)

        improved, _ = two_opt(cost, start)

        assert improved[0] == 0
        assert sorted(improved) == list(range(9))
        assert route_cost(cost, improved) <= route_cost(cost, start) + 1e-12


def test_exact_optimum_matches_a_plain_brute_force_and_counts_every_order():
    for seed in range(5):
        cost = asymmetric_costs(7, seed)

        route, evaluated = exact_optimum(cost)

        assert evaluated == 720
        assert route[0] == 0
        assert abs(route_cost(cost, route) - brute_force(cost)) < 1e-12


def test_exact_optimum_is_never_worse_than_the_heuristic():
    cost = asymmetric_costs(8, 42)
    heuristic, _ = two_opt(cost, nearest_neighbour(cost))

    optimum, _ = exact_optimum(cost)

    assert route_cost(cost, optimum) <= route_cost(cost, heuristic) + 1e-12
