"""Polynomial coordinate transitions between equidistant regions."""

import numpy as np
from numpy.typing import NDArray


def build_cubic_transition(
    start: float,
    end: float,
    n_points: int,
    start_spacing: float,
) -> NDArray[np.float64]:
    """Build a cubic transition matching location, spacing, and curvature at its start."""

    n_intervals = n_points - 1
    parameter = np.linspace(0.0, 1.0, n_points)
    start_derivative = n_intervals * start_spacing
    cubic_coefficient = end - start - start_derivative
    coordinates = start + start_derivative * parameter + cubic_coefficient * parameter**3
    coordinates[-1] = end
    return coordinates


def build_quintic_transition(
    start: float,
    end: float,
    n_points: int,
    start_spacing: float,
    end_spacing: float,
) -> NDArray[np.float64]:
    """Build a quintic transition matching adjacent linear regions through curvature."""

    n_intervals = n_points - 1
    start_derivative = n_intervals * start_spacing
    end_derivative = n_intervals * end_spacing

    matrix = np.array(
        [
            [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 2.0, 0.0, 0.0, 0.0],
            [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
            [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
            [0.0, 0.0, 2.0, 6.0, 12.0, 20.0],
        ]
    )
    constraints = np.array([start, start_derivative, 0.0, end, end_derivative, 0.0])
    coefficients = np.linalg.solve(matrix, constraints)

    parameter = np.linspace(0.0, 1.0, n_points)
    coordinates = np.polynomial.polynomial.polyval(parameter, coefficients)
    coordinates[0] = start
    coordinates[-1] = end
    return coordinates
