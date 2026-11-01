"""Cartesian tensor-product grid generation."""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
from __future__ import annotations

from pathlib import Path

import numpy as np
from cfd_io import Dataset, StructuredGrid

from grid_generator.config import CartesianConfig, load_cartesian_config
from grid_generator.config.cartesian import AXIS_MARKER_KEYS
from grid_generator.distributions import build_distribution

# --------------------------------------------------
# constants
# --------------------------------------------------
# grid side of each [markers] key (the names themselves come from the config)
MARKER_SIDES = {
    "x_min": "imin",
    "x_max": "imax",
    "y_min": "jmin",
    "y_max": "jmax",
    "z_min": "kmin",
    "z_max": "kmax",
}


# --------------------------------------------------
# public API
# --------------------------------------------------
def generate_cartesian(source: CartesianConfig | str | Path) -> Dataset:
    """Generate a Cartesian grid from a config object or TOML file.

    Args:
        source: Validated configuration or configuration file path.

    Returns:
        Grid-only CFD dataset with physical coordinate arrays and the boundary markers
        of the axes the grid has.
    """

    # load configuration when the caller supplied an artifact path
    if isinstance(source, CartesianConfig):
        config = source
    else:
        config = load_cartesian_config(source)

    # build active axes and singleton coordinates for omitted dimensions
    x_axis = build_distribution(config.x)
    y_axis = build_distribution(config.y) if config.y is not None else np.array([0.0])
    z_axis = build_distribution(config.z) if config.z is not None else np.array([0.0])

    # assemble physical coordinates in cfd-io's (ni, nj, nk) convention
    grid_x, grid_y, grid_z = np.meshgrid(x_axis, y_axis, z_axis, indexing="ij")
    grid = StructuredGrid(x=grid_x, y=grid_y, z=grid_z)

    # markers: both ends of each axis the grid has, named by [markers]
    active_axes = {"x": config.x, "y": config.y, "z": config.z}
    markers = {}
    for axis_name, axis_spec in active_axes.items():
        if axis_spec is None:
            continue
        for key in AXIS_MARKER_KEYS[axis_name]:
            markers[MARKER_SIDES[key]] = getattr(config.markers, key)

    dimensionality = 1 + int(config.y is not None) + int(config.z is not None)
    dataset = Dataset(
        grid=grid,
        attrs={
            "dataset_type": "grid",
            "grid_type": "cartesian",
            "coordinate_system": "cartesian",
            "dimensionality": dimensionality,
            "producer": "grid-generator",
            "ni": grid.shape[0],
            "nj": grid.shape[1],
            "nk": grid.shape[2],
            "markers": {"structured": markers},
        },
    )
    return dataset
