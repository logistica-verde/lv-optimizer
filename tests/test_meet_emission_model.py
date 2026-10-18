import numpy as np
import pytest

from app.optimization.meet_emission_model import MeetEmissionModel, vehicle_class_for


def test_base_emission_follows_table_a24_for_light_hgv():
    model = MeetEmissionModel(7500.0)

    emission = model.base_emission_g_per_km(50.0)

    assert emission == pytest.approx(110 + 0.000375 * 50**3 + 8702 / 50)


def test_base_emission_follows_table_a25_for_medium_hgv():
    model = MeetEmissionModel(12000.0)

    emission = model.base_emission_g_per_km(40.0)

    assert emission == pytest.approx(871 - 16.0 * 40 + 0.143 * 40**2 + 32031 / 40**2)


@pytest.mark.parametrize(
    "mass_kg, expected",
    [
        (3000.0, "HGV 3.5-7.5 t"),
        (7500.0, "HGV 3.5-7.5 t"),
        (7501.0, "HGV 7.5-16 t"),
        (20000.0, "HGV 16-32 t"),
        (40000.0, "HGV 32-40 t"),
        (50000.0, "HGV 32-40 t"),
    ],
)
def test_vehicle_class_is_chosen_by_gross_mass(mass_kg, expected):
    assert vehicle_class_for(mass_kg).name == expected


def test_gradient_factor_is_one_on_a_flat_road():
    model = MeetEmissionModel(7500.0)

    assert model.gradient_factor(50.0, 0.0) == pytest.approx(1.0)


def test_gradient_factor_follows_table_a37_uphill_class():
    model = MeetEmissionModel(7500.0)
    v = 30.0

    factor = model.gradient_factor(v, 2.0)

    expected = (
        -3.01e-09 * v**5 + 5.73e-07 * v**4 - 4.13e-05 * v**3 + 1.13e-03 * v**2 + 8.13e-03 * v + 9.14e-01
    )
    assert factor == pytest.approx(expected)


def test_gradient_factor_clamps_speed_to_the_class_validity_range():
    model = MeetEmissionModel(7500.0)

    assert model.gradient_factor(90.0, 5.0) == pytest.approx(model.gradient_factor(39.3, 5.0))
    assert model.gradient_factor(5.0, 5.0) == pytest.approx(model.gradient_factor(13.0, 5.0))


def test_uphill_emits_more_and_downhill_less_than_flat():
    model = MeetEmissionModel(7500.0)

    flat = model.calculate_emission(40.0, 0.0, 1.0)

    assert model.calculate_emission(40.0, 3.0, 1.0) > flat
    assert model.calculate_emission(40.0, 5.0, 1.0) > model.calculate_emission(40.0, 3.0, 1.0)
    assert model.calculate_emission(40.0, -3.0, 1.0) < flat


def test_load_factor_follows_table_a43_when_fully_loaded():
    model = MeetEmissionModel(7500.0, load_ratio=1.0)
    v, g = 50.0, 2.0

    factor = model.load_factor(v, g)

    assert factor == pytest.approx(1.27 + 0.0614 * g - 0.00110 * g**3 - 0.00235 * v - 1.33 / v)


def test_unloaded_vehicle_has_no_load_correction():
    model = MeetEmissionModel(7500.0, load_ratio=0.0)

    assert model.load_factor(50.0, 2.0) == pytest.approx(1.0)


def test_load_correction_is_interpolated_by_load_ratio():
    full = MeetEmissionModel(7500.0, load_ratio=1.0).load_factor(50.0, 0.0)
    half = MeetEmissionModel(7500.0, load_ratio=0.5).load_factor(50.0, 0.0)

    assert half == pytest.approx(1.0 + (full - 1.0) / 2)


def test_calculate_emission_combines_base_gradient_load_and_distance():
    model = MeetEmissionModel(7500.0)
    v, g, d = 30.0, -2.0, 2.5

    emission = model.calculate_emission(v, g, d)

    expected = model.base_emission_g_per_km(v) * model.gradient_factor(v, g) * model.load_factor(v, g) * d
    assert emission == pytest.approx(expected)


def test_calculate_emission_is_vectorized_over_legs():
    model = MeetEmissionModel(7500.0)
    speeds = np.array([20.0, 40.0, 60.0])
    slopes = np.array([-5.0, 0.0, 3.0])
    distances = np.array([1.0, 2.0, 3.0])

    emissions = model.calculate_emission(speeds, slopes, distances)

    expected = [float(model.calculate_emission(v, g, d)) for v, g, d in zip(speeds, slopes, distances)]
    assert emissions.tolist() == pytest.approx(expected)


def test_emission_is_positive_on_every_gradient_class():
    model = MeetEmissionModel(7500.0)
    slopes = np.array([-8.0, -5.0, -2.0, 0.0, 2.0, 5.0, 8.0])

    assert np.all(model.calculate_emission(np.full(7, 40.0), slopes, np.ones(7)) > 0)
