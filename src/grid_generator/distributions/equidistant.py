"""Equidistant one-dimensional point distribution."""

import numpy as np
from numpy.typing import NDArray

from grid_generator.distributions.models import EquidistantSpec


def build_equidistant(spec: EquidistantSpec) -> NDArray[np.float64]:
    """Build an equidistant coordinate array."""

    coordinates = np.linspace(spec.start, spec.end, spec.n_points)
    return coordinates
