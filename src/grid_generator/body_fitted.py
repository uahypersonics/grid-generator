"""Constant-height body-fitted 2D grid generation.

Wall points (i) run from the stagnation point, around the nose, along the body to
x_end. Each j-line runs straight out along the exact wall normal to the same
height H:

    x(i, j) = wall(s_i) + n_j * normal(s_i)

The nose and the body get separate wall distributions that meet at the junction:
equal steps in arc length on the nose (equal steps in angle, so the nose block is
polar about the nose centre), then geometric growth along the body starting from
the nose spacing, so the spacing is continuous across the junction.

No shock alignment yet: H is constant, and the user picks it large enough to
clear the bow shock.
"""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
from __future__ import annotations

from pathlib import Path

import numpy as np
from canonical_geometries import Profile2D
from cfd_io import Dataset, StructuredGrid
from numpy.typing import NDArray

from grid_generator.config.body_fitted import BodyFittedConfig, load_body_fitted_config
from grid_generator.distributions import EquidistantSpec, GeometricSpec, build_distribution

# --------------------------------------------------
# constants
# --------------------------------------------------

# SU2 / Gmsh boundary names for the four sides of the grid: imin is the stagnation
# line ahead of the nose, imax the outflow at x_end, jmin the wall, jmax the outer
# boundary
BOUNDARY_MARKERS = {
    "imin": "symmetry",
    "imax": "outflow",
    "jmin": "wall",
    "jmax": "farfield",
}


# --------------------------------------------------
# public API
# --------------------------------------------------
def generate_body_fitted(source: BodyFittedConfig | str | Path) -> Dataset:
    """Generate a constant-height body-fitted 2D grid from a config object or TOML file.

    Args:
        source: Validated configuration or configuration file path.

    Returns:
        Grid-only CFD dataset with shape (ni, nj, 1) in cfd-io's convention, with the
        boundary markers SU2 output needs.
    """

    # load configuration when the caller supplied a file path
    if isinstance(source, BodyFittedConfig):
        config = source
    else:
        config = load_body_fitted_config(source)

    # wall profile, truncated at x_end
    profile = config.build_profile()

    # arc lengths of the wall points: nose, then body
    s_wall = wall_arc_lengths(profile, config.points.n_nose, config.points.n_body)

    # wall-normal distances: geometric growth from the first spacing up to the height
    normal_spec = GeometricSpec(
        start=0.0,
        end=config.domain.height,
        n_points=config.points.n_normal,
        first_spacing=config.points.first_normal_spacing,
    )
    n_dist = build_distribution(normal_spec)

    # exact wall points and normals
    x_wall, y_wall = profile.point(s_wall)
    nx, ny = profile.normal(s_wall)

    # j-lines straight out along the wall normals: (ni, nj)
    x_plane = x_wall[:, None] + n_dist[None, :] * nx[:, None]
    y_plane = y_wall[:, None] + n_dist[None, :] * ny[:, None]

    # cfd-io's (ni, nj, nk) layout with nk = 1, in the z = 0 plane
    x = x_plane[:, :, None]
    y = y_plane[:, :, None]
    z = np.zeros_like(x)
    grid = StructuredGrid(x=x, y=y, z=z)

    # describe the grid; markers are what cfd-io's SU2 writer needs
    geometry_type = config.geometry.type
    dataset = Dataset(
        grid=grid,
        attrs={
            "dataset_type": "grid",
            "grid_type": "body-fitted",
            "coordinate_system": "cartesian",
            "dimensionality": 2,
            "producer": "grid-generator",
            "geometry_type": geometry_type,
            "axisymmetric": geometry_type == "cone",
            "ni": grid.shape[0],
            "nj": grid.shape[1],
            "nk": grid.shape[2],
            "markers": {"structured": dict(BOUNDARY_MARKERS)},
        },
    )
    return dataset


def wall_arc_lengths(profile: Profile2D, n_nose: int, n_body: int) -> NDArray[np.float64]:
    """Arc lengths of the wall points: equidistant on the nose, geometric on the body.

    The nose ends exactly at the profile's junction. The body's first spacing equals
    the nose spacing, so the spacing is continuous across the junction.

    Args:
        profile: Wall profile with one junction (nose, then body).
        n_nose: Points on the nose, including both ends.
        n_body: Points on the body, including both ends.

    Returns:
        Arc lengths of the n_nose + n_body - 1 wall points (the junction appears once).

    Raises:
        ValueError: If the profile doesn't have exactly one junction.
    """

    # validate inputs
    junctions = np.asarray(profile.junctions, dtype=float)
    if junctions.size != 1:
        raise ValueError(f"expected a profile with one junction (nose, body), got {junctions.size}")
    s_junction = float(junctions[0])

    # nose: equal arc-length steps, i.e. equal angle steps on the circular arc
    nose_spec = EquidistantSpec(start=0.0, end=s_junction, n_points=n_nose)
    s_nose = build_distribution(nose_spec)
    nose_spacing = s_junction / (n_nose - 1)

    # body: geometric growth starting from the nose spacing
    body_spec = GeometricSpec(
        start=s_junction,
        end=profile.total_length,
        n_points=n_body,
        first_spacing=nose_spacing,
    )
    s_body = build_distribution(body_spec)

    # join, keeping the shared junction point once
    s_wall = np.concatenate([s_nose, s_body[1:]])

    return s_wall
