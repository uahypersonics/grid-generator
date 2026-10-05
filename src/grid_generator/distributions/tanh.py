"""Hyperbolic-tangent one-dimensional point distribution."""

import numpy as np
from numpy.typing import NDArray

from grid_generator.distributions.models import TanhSpec


def build_tanh(spec: TanhSpec) -> NDArray[np.float64]:
    """Build a tanh-clustered coordinate array."""

    parameter = np.linspace(0.0, 1.0, spec.n_points)
    normalization = np.tanh(spec.strength)

    if spec.cluster == "start":
        mapped = 1.0 - np.tanh(spec.strength * (1.0 - parameter)) / normalization
    elif spec.cluster == "end":
        mapped = np.tanh(spec.strength * parameter) / normalization
    else:
        centered = 2.0 * parameter - 1.0
        mapped = 0.5 * (1.0 + np.tanh(spec.strength * centered) / normalization)

    coordinates = spec.start + (spec.end - spec.start) * mapped
    coordinates[0] = spec.start
    coordinates[-1] = spec.end
    return coordinates
