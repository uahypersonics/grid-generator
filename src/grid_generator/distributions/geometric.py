"""Geometric one-dimensional point distribution."""

import numpy as np
from numpy.typing import NDArray

from grid_generator.distributions.models import GeometricSpec


def build_geometric(spec: GeometricSpec) -> NDArray[np.float64]:
    """Build a geometric coordinate array with exact endpoints."""

    # capped growth has its own solver
    if spec.max_spacing is not None:
        coordinates = _build_capped(spec)
        return coordinates

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


def _build_capped(spec: GeometricSpec) -> NDArray[np.float64]:
    """Geometric growth from first_spacing up to max_spacing, then uniform at max_spacing.

    The ratio is solved so the n_points - 1 spacings, min(first * ratio^k, max),
    add up to the length. Their sum grows with the ratio, so bisection finds it.
    The spec's validation guarantees a solution with ratio > 1.
    """

    # extract
    length = spec.end - spec.start
    n_intervals = spec.n_points - 1
    first_spacing = float(spec.first_spacing)
    max_spacing = float(spec.max_spacing)
    powers = np.arange(n_intervals, dtype=np.float64)

    # bracket the ratio: 1 is too short (validated); double the upper bound until long enough
    lower = 1.0
    upper = 2.0
    while _capped_sum(upper, powers, first_spacing, max_spacing) < length:
        upper *= 2.0

    # bisect
    for _ in range(200):
        midpoint = 0.5 * (lower + upper)
        if _capped_sum(midpoint, powers, first_spacing, max_spacing) < length:
            lower = midpoint
        else:
            upper = midpoint
    ratio = 0.5 * (lower + upper)

    # spacings, scaled by the leftover round-off so the end is hit exactly
    spacings = _capped_spacings(ratio, powers, first_spacing, max_spacing)
    spacings *= length / np.sum(spacings)

    # coordinates with exact endpoints
    offsets = np.concatenate((np.array([0.0]), np.cumsum(spacings)))
    coordinates = spec.start + offsets
    coordinates[-1] = spec.end
    return coordinates


def _capped_spacings(
    ratio: float, powers: NDArray[np.float64], first_spacing: float, max_spacing: float
) -> NDArray[np.float64]:
    """Spacings first * ratio^k, capped at max_spacing (log form avoids overflow)."""

    # growth in log space, then cap
    log_spacings = np.log(first_spacing) + powers * np.log(ratio)
    spacings = np.exp(np.minimum(log_spacings, np.log(max_spacing)))
    return spacings


def _capped_sum(
    ratio: float, powers: NDArray[np.float64], first_spacing: float, max_spacing: float
) -> float:
    """Total length covered by the capped spacings."""

    total = float(np.sum(_capped_spacings(ratio, powers, first_spacing, max_spacing)))
    return total
