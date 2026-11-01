"""Constant-height body-fitted 2D grid generation.

Wall points (i) run from the stagnation point, around the nose, along the body to
x_end. Each j-line runs straight out along the exact wall normal to the same
height H:

    x(i, j) = wall(s_i) + n_j * normal(s_i)

The nose and the body get separate wall distributions that meet at the junction:
equal steps in arc length on the nose (equal steps in angle, so the nose block is
polar about the nose centre), then the configured body distribution starting from
the nose spacing, so the spacing is continuous across the junction. The body may be
straight (plate, wedge, cone) or curved (tangent ogive, with an optional cylinder).

No shock alignment yet: H is constant, and the user picks it large enough to
clear the bow shock.

With a [span] table (plate and wedge), the 2D plane is extruded in z: the same
(x, y) plane at every z of the span distribution, giving a 3D grid.
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

from grid_generator.config.body_fitted import (
    AXISYMMETRIC_TYPES,
    BodyFittedConfig,
    load_body_fitted_config,
)
from grid_generator.distributions import DistributionSpec, EquidistantSpec, build_distribution

# --------------------------------------------------
# constants
# --------------------------------------------------

# grid side of each [markers] key (the names themselves come from the config): imin is
# the stagnation line ahead of the nose, imax the outflow at x_end, jmin the wall,
# jmax the outer boundary
MARKER_SIDES = {
    "symmetry": "imin",
    "outflow": "imax",
    "wall": "jmin",
    "outer": "jmax",
}

# the two extra sides of an extruded (3D) grid: the first and last z-planes; the
# solver decides what they are (periodic, symmetry, ...)
SPAN_MARKER_SIDES = {
    "span_min": "kmin",
    "span_max": "kmax",
}


# --------------------------------------------------
# public API
# --------------------------------------------------
def generate_body_fitted(source: BodyFittedConfig | str | Path) -> Dataset:
    """Generate a constant-height body-fitted grid from a config object or TOML file.

    The grid is 2D, or 3D when the config has a [span] to extrude it in z.

    Args:
        source: Validated configuration or configuration file path.

    Returns:
        Grid-only CFD dataset with shape (ni, nj, 1), or (ni, nj, nk) when extruded, in
        cfd-io's convention, with the boundary markers SU2 output needs.
    """

    # load configuration when the caller supplied a file path
    if isinstance(source, BodyFittedConfig):
        config = source
    else:
        config = load_body_fitted_config(source)

    # wall profile, truncated at x_end
    profile = config.build_profile()

    # arc lengths of the wall points: nose, then body
    s_wall = wall_arc_lengths(profile, config.points.nose.n_points, config.body_distribution())

    # wall-normal distances: from the wall up to the height
    n_dist = build_distribution(config.normal_distribution())

    # exact wall points and normals
    x_wall, y_wall = profile.point(s_wall)
    nx, ny = profile.normal(s_wall)

    # j-lines straight out along the wall normals: (ni, nj)
    x_plane = x_wall[:, None] + n_dist[None, :] * nx[:, None]
    y_plane = y_wall[:, None] + n_dist[None, :] * ny[:, None]

    # span: the z-planes to extrude to, or the single plane z = 0 for a 2D grid
    if config.span is not None:
        z_axis = build_distribution(config.span)
    else:
        z_axis = np.array([0.0])
    nk = z_axis.size

    # cfd-io's (ni, nj, nk) layout: the same (x, y) plane at every z
    x = np.repeat(x_plane[:, :, None], nk, axis=2)
    y = np.repeat(y_plane[:, :, None], nk, axis=2)
    z = np.broadcast_to(z_axis[None, None, :], x.shape).copy()
    grid = StructuredGrid(x=x, y=y, z=z)

    # markers: four sides in 2D, plus the two z-planes in 3D, named by [markers]
    markers = {}
    for key, side in MARKER_SIDES.items():
        markers[side] = getattr(config.markers, key)
    if nk > 1:
        for key, side in SPAN_MARKER_SIDES.items():
            markers[side] = getattr(config.markers, key)
    dimensionality = 3 if nk > 1 else 2

    # describe the grid; markers are what cfd-io's SU2 writer needs
    geometry_type = config.geometry.type
    dataset = Dataset(
        grid=grid,
        attrs={
            "dataset_type": "grid",
            "grid_type": "body-fitted",
            "coordinate_system": "cartesian",
            "dimensionality": dimensionality,
            "producer": "grid-generator",
            "geometry_type": geometry_type,
            "axisymmetric": geometry_type in AXISYMMETRIC_TYPES,
            "ni": grid.shape[0],
            "nj": grid.shape[1],
            "nk": grid.shape[2],
            "markers": {"structured": markers},
        },
    )
    return dataset


def wall_arc_lengths(
    profile: Profile2D, n_nose: int, body_spec: DistributionSpec
) -> NDArray[np.float64]:
    """Arc lengths of the wall points: equidistant on the nose, then the body distribution.

    The nose ends exactly at the profile's junction. The body distribution starts there,
    at the nose spacing (BodyFittedConfig.body_distribution builds it that way), so the
    spacing is continuous across the junction.

    Args:
        profile: Wall profile; its first junction is the end of the nose (later junctions,
            e.g. an ogive base, lie inside the body distribution).
        n_nose: Points on the nose, including both ends.
        body_spec: Body distribution in wall arc length, from the junction to the end.

    Returns:
        Arc lengths of the wall points: n_nose + body points - 1 (the junction appears once).

    Raises:
        ValueError: If the profile has no junction (no nose).
    """

    # validate inputs
    junctions = np.asarray(profile.junctions, dtype=float)
    if junctions.size == 0:
        raise ValueError("expected a profile with a nose junction, got none")
    s_junction = float(junctions[0])

    # nose: equal arc-length steps, i.e. equal angle steps on the circular arc
    nose_spec = EquidistantSpec(start=0.0, end=s_junction, n_points=n_nose)
    s_nose = build_distribution(nose_spec)

    # body: the configured distribution, starting at the junction
    s_body = build_distribution(body_spec)

    # join, keeping the shared junction point once
    s_wall = np.concatenate([s_nose, s_body[1:]])

    return s_wall
