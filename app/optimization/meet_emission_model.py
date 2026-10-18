"""CO2 emissions of heavy goods vehicles by the MEET model, E = f(v, m, i).

Source: Hickman et al. (1999), Methodology for calculating transport emissions and energy
consumption, TRL Project Report SE/491/98, Annex A. Equation and table numbers below refer
to that report.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class GradientFactor:
    """Equation A11 for one gradient class: as = A6*v^6 + ... + A1*v + A0, valid in [v_min, v_max]."""

    slope_min_percent: float
    slope_max_percent: float
    coefficients: tuple[float, float, float, float, float, float, float]
    v_min_kmh: float
    v_max_kmh: float


@dataclass(frozen=True)
class VehicleClass:
    """Equation A10 (K, a..f), A11 gradient classes and A14 load correction (k, n..u) for CO2."""

    name: str
    max_mass_kg: float
    emission: tuple[float, float, float, float, float, float, float]
    gradient: tuple[GradientFactor, ...]
    load: tuple[float, float, float, float, float, float, float, float]


HGV_CLASSES = (
    VehicleClass(
        name="HGV 3.5-7.5 t",
        max_mass_kg=7_500.0,
        emission=(110.0, 0.0, 0.0, 0.000375, 8702.0, 0.0, 0.0),  # Table A24
        gradient=(  # Table A37
            GradientFactor(4, 6, (0.0, 4.27e-07, -5.74e-05, 2.97e-03, -7.43e-02, 9.35e-01, -3.03), 13.0, 39.3),
            GradientFactor(-6, -4, (0.0, -7.74e-08, 1.33e-05, -8.78e-04, 2.72e-02, -3.93e-01, 2.65), 13.5, 49.9),
            GradientFactor(0, 4, (0.0, -3.01e-09, 5.73e-07, -4.13e-05, 1.13e-03, 8.13e-03, 9.14e-01), 15.1, 69.9),
            GradientFactor(-4, 0, (0.0, -1.39e-10, 5.03e-08, -4.18e-06, 1.95e-05, 3.68e-03, 6.69e-01), 15.1, 86.2),
        ),
        load=(1.27, 0.0614, 0.0, -0.00110, -0.00235, 0.0, 0.0, -1.33),  # Table A43
    ),
    VehicleClass(
        name="HGV 7.5-16 t",
        max_mass_kg=16_000.0,
        emission=(871.0, -16.0, 0.143, 0.0, 0.0, 32031.0, 0.0),  # Table A25
        gradient=(  # Table A38
            GradientFactor(4, 6, (0.0, 3.21e-07, -4.29e-05, 2.23e-03, -5.75e-02, 7.62e-01, -1.98), 13.1, 39.5),
            GradientFactor(-6, -4, (0.0, -1.24e-07, 2.08e-05, -1.33e-03, 4.00e-02, -5.65e-01, 3.57), 13.5, 49.9),
            GradientFactor(0, 4, (0.0, -9.78e-10, -2.01e-09, 1.91e-05, -1.63e-03, 5.91e-02, 7.70e-01), 15.1, 70.3),
            GradientFactor(-4, 0, (0.0, -6.04e-11, -2.36e-08, 7.76e-06, -6.83e-04, 1.79e-02, 6.12e-01), 15.1, 86.4),
        ),
        load=(1.26, 0.0790, 0.0, -0.00109, 0.0, 0.0, -2.03e-07, -1.14),  # Table A44
    ),
    VehicleClass(
        name="HGV 16-32 t",
        max_mass_kg=32_000.0,
        emission=(765.0, -7.04, 0.0, 0.000632, 8334.0, 0.0, 0.0),  # Table A26
        gradient=(  # Table A39
            GradientFactor(4, 6, (0.0, 0.0, -6.69e-06, 6.55e-04, -2.31e-02, 3.69e-01, 1.07e-01), 12.5, 36.5),
            GradientFactor(-6, -4, (0.0, -1.22e-07, 2.03e-05, -1.30e-03, 3.94e-02, -5.70e-01, 3.75), 13.5, 49.9),
            GradientFactor(0, 4, (0.0, -5.25e-09, 9.93e-07, -6.74e-05, 2.06e-03, -1.96e-02, 1.45), 14.9, 64.7),
            GradientFactor(-4, 0, (0.0, -8.24e-11, 2.91e-08, -2.58e-06, 5.76e-05, -4.74e-03, 8.55e-01), 15.1, 86.1),
        ),
        load=(1.27, 0.0882, 0.0, -0.00101, 0.0, 0.0, 0.0, -0.483),  # Table A45
    ),
    VehicleClass(
        name="HGV 32-40 t",
        max_mass_kg=40_000.0,
        emission=(1576.0, -17.6, 0.0, 0.00117, 0.0, 36067.0, 0.0),  # Table A27
        gradient=(  # Table A40
            GradientFactor(4, 6, (0.0, 5.88e-07, -7.24e-05, 3.45e-03, -7.86e-02, 8.63e-01, -9.76e-01), 12.4, 35.0),
            GradientFactor(-6, -4, (0.0, -1.18e-07, 2.00e-05, -1.29e-03, 3.96e-02, -5.78e-01, 3.72), 13.5, 49.9),
            GradientFactor(0, 4, (0.0, -2.04e-09, 4.35e-07, -3.69e-05, 1.69e-03, -3.16e-02, 1.77), 14.8, 66.3),
            GradientFactor(-4, 0, (0.0, -1.10e-09, 2.69e-07, -2.38e-05, 9.51e-04, -2.24e-02, 9.16e-01), 15.1, 86.3),
        ),
        load=(1.43, 0.121, 0.0, -0.00125, 0.0, 0.0, 0.0, -0.916),  # Table A46
    ),
)


def vehicle_class_for(vehicle_mass_kg: float) -> VehicleClass:
    """Class by gross vehicle weight; below 3.5 t uses the lightest class, above 40 t the heaviest."""
    for vehicle_class in HGV_CLASSES:
        if vehicle_mass_kg <= vehicle_class.max_mass_kg:
            return vehicle_class
    return HGV_CLASSES[-1]


class MeetEmissionModel:
    """CO2 in grams for a goods vehicle of gross mass m on a leg with mean speed v and gradient i.

    load_ratio scales the load correction linearly between unloaded (0) and fully loaded (1).
    """

    def __init__(self, vehicle_mass_kg: float, load_ratio: float = 1.0):
        self.vehicle_mass_kg = vehicle_mass_kg
        self.load_ratio = load_ratio
        self.vehicle_class = vehicle_class_for(vehicle_mass_kg)

    def base_emission_g_per_km(self, velocity_kmh):
        """Equation A10: unloaded vehicle on a 0% gradient."""
        k, a, b, c, d, e, f = self.vehicle_class.emission
        v = np.maximum(np.asarray(velocity_kmh, dtype=float), 1e-3)
        return k + a * v + b * v**2 + c * v**3 + d / v + e / v**2 + f / v**3

    def gradient_factor(self, velocity_kmh, slope_percent):
        """Equation A11, speed clamped to each class's validity range; 1 on a flat road."""
        v = np.asarray(velocity_kmh, dtype=float)
        slope = np.asarray(slope_percent, dtype=float)
        v, slope = np.broadcast_arrays(v, slope)
        factor = np.ones(v.shape)
        for gradient in self.vehicle_class.gradient:
            in_class = self._in_gradient_class(slope, gradient)
            clamped = np.clip(v, gradient.v_min_kmh, gradient.v_max_kmh)
            factor = np.where(in_class, np.polyval(gradient.coefficients, clamped), factor)
        return factor

    @staticmethod
    def _in_gradient_class(slope: np.ndarray, gradient: GradientFactor) -> np.ndarray:
        if gradient.slope_min_percent >= 4:
            return slope > 4
        if gradient.slope_max_percent <= -4:
            return slope < -4
        if gradient.slope_min_percent >= 0:
            return (slope > 0) & (slope <= 4)
        return (slope < 0) & (slope >= -4)

    def load_factor(self, velocity_kmh, slope_percent):
        """Equation A13 with A14 for a fully loaded vehicle, interpolated by load_ratio."""
        k, n, p, q, r, s, t, u = self.vehicle_class.load
        v = np.maximum(np.asarray(velocity_kmh, dtype=float), 1e-3)
        g = np.asarray(slope_percent, dtype=float)
        full_load = k + n * g + p * g**2 + q * g**3 + r * v + s * v**2 + t * v**3 + u / v
        return 1.0 + self.load_ratio * (full_load - 1.0)

    def calculate_emission(self, velocity_kmh, slope_percent, distance_km):
        """Equation A12: emission in grams over the given distance."""
        return (
            self.base_emission_g_per_km(velocity_kmh)
            * self.gradient_factor(velocity_kmh, slope_percent)
            * self.load_factor(velocity_kmh, slope_percent)
            * np.asarray(distance_km, dtype=float)
        )
