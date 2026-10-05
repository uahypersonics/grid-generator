"""Geometric one-dimensional point distribution."""

import numpy as np
from numpy.typing import NDArray

from grid_generator.distributions.models import GeometricSpec


def build_geometric(spec: GeometricSpec) -> NDArray[np.float64]:
    """Build a geometric coordinate array with exact endpoints."""

    ratio = spec.ratio
    if ratio is None:
        ratio = _solve_ratio(
            length=spec.end - spec.start,
            n_intervals=spec.n_points - 1,
            first_spacing=float(spec.first_spacing),
        )

    n_intervals = spec.n_points - 1
    if np.isclose(ratio, 1.0):
        coordinates = np.linspace(spec.start, spec.end, spec.n_points)
        return coordinates

    weights = ratio ** np.arange(n_intervals, dtype=np.float64)
    spacings = (spec.end - spec.start) * weights / np.sum(weights)
    offsets = np.concatenate((np.array([0.0]), np.cumsum(spacings)))
    coordinates = spec.start + offsets
    coordinates[-1] = spec.end
    return coordinates


def _solve_ratio(length: float, n_intervals: int, first_spacing: float) -> float:
    """Solve the geometric ratio from the requested first spacing."""

    target_sum = length / first_spacing
    uniform_sum = float(n_intervals)
    if np.isclose(target_sum, uniform_sum):
        return 1.0

    if target_sum < uniform_sum:
        lower = 0.0
        upper = 1.0
    else:
        lower = 1.0
        upper = 2.0
        while _geometric_sum(upper, n_intervals, target_sum) < target_sum:
            upper *= 2.0

    for _ in range(100):
        midpoint = 0.5 * (lower + upper)
        midpoint_sum = _geometric_sum(midpoint, n_intervals, target_sum)
        if midpoint_sum < target_sum:
            lower = midpoint
        else:
            upper = midpoint

    ratio = 0.5 * (lower + upper)
    return ratio


def _geometric_sum(ratio: float, n_intervals: int, limit: float) -> float:
    """Evaluate a geometric sum while avoiding unnecessary overflow."""

    total = 0.0
    term = 1.0
    for _ in range(n_intervals):
        total += term
        if total >= limit:
            break
        term *= ratio
    return total
