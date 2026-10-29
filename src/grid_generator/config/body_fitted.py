"""Configuration contract for constant-height body-fitted 2D grids.

The [geometry] table is canonical-geometries' contract (plate, wedge, cone), so one
geometry definition works in both tools. The config is parsed and validated with
pydantic; the generator works from the validated object.
"""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from canonical_geometries import BluntedWedge
from canonical_geometries.config import GeometryConfig
from pydantic import BaseModel, ConfigDict, Field, model_validator


# --------------------------------------------------
# tables
# --------------------------------------------------
class DomainConfig(BaseModel):
    """Extent of the grid: where it ends along x, and how far it reaches from the wall."""

    # reject misspelled keys
    model_config = ConfigDict(extra="forbid")

    x_end: float = Field(gt=0.0, description="End of the grid along x, from the nose tip [m]")
    height: float = Field(gt=0.0, description="Constant wall-normal height of the grid [m]")


class PointsConfig(BaseModel):
    """Point counts along the wall (nose, body) and away from it."""

    # reject misspelled keys
    model_config = ConfigDict(extra="forbid")

    n_nose: int = Field(ge=2, description="Points on the nose arc, equally spaced in angle")
    n_body: int = Field(ge=2, description="Points on the body, geometric growth from the nose")
    n_normal: int = Field(ge=2, description="Points in the wall-normal direction")
    first_normal_spacing: float = Field(gt=0.0, description="First wall-normal spacing [m]")


class OutputConfig(BaseModel):
    """Grid file; a relative path is resolved against the config file's folder."""

    # reject misspelled keys
    model_config = ConfigDict(extra="forbid")

    filename: Path = Field(description="Grid file; the extension picks the format via cfd-io")
    order: Literal[1, 2] = Field(
        default=1,
        description="Element order for .msh: 1 (4-node quads) or 2 (curved 9-node quads)",
    )

    @model_validator(mode="after")
    def _check_order_fits_the_format(self) -> OutputConfig:
        """Only Gmsh output has second-order elements."""

        # order 2 means 9-node quads, which only the .msh writer produces
        suffix = self.filename.suffix.lower()
        if self.order == 2 and suffix != ".msh":
            raise ValueError(f"[output] order = 2 needs a .msh filename (Gmsh), got {suffix!r}")

        return self


# --------------------------------------------------
# whole file
# --------------------------------------------------
class BodyFittedConfig(BaseModel):
    """Contents of a body-fitted grid TOML file."""

    # reject unknown sections
    model_config = ConfigDict(extra="forbid")

    geometry: GeometryConfig
    domain: DomainConfig
    points: PointsConfig
    output: OutputConfig

    @model_validator(mode="after")
    def _check_domain_fits_the_geometry(self) -> BodyFittedConfig:
        """Check x_end lies on the body, and the first normal spacing fits in the height."""

        # x_end can't go past the end of the geometry
        x_end = self.domain.x_end
        if x_end > self.geometry.length:
            raise ValueError(
                f"[domain] x_end ({x_end}) must not exceed [geometry] length "
                f"({self.geometry.length})"
            )

        # x_end must reach past the nose (building the truncated profile checks this)
        try:
            self.build_profile()
        except ValueError as error:
            raise ValueError(
                f"[domain] x_end ({x_end}) must reach past the nose: {error}"
            ) from None

        # the first wall-normal cell must fit inside the grid height
        if self.points.first_normal_spacing >= self.domain.height:
            raise ValueError(
                f"[points] first_normal_spacing ({self.points.first_normal_spacing}) must be "
                f"smaller than [domain] height ({self.domain.height})"
            )

        # second-order elements span 2 x 2 grid cells: odd point counts, and an odd
        # n_nose puts the nose/body junction on an element corner, not inside an element
        if self.output.order == 2:
            even_counts = []
            for name in ("n_nose", "n_body", "n_normal"):
                count = getattr(self.points, name)
                if count % 2 == 0:
                    even_counts.append(f"{name} = {count}")
            if even_counts:
                raise ValueError(
                    f"[output] order = 2 needs odd point counts; even: {', '.join(even_counts)}"
                )

        return self

    def build_profile(self) -> BluntedWedge:
        """Build the wall profile truncated at x_end."""

        # same geometry, cut off at the end of the grid
        truncated = self.geometry.model_copy(update={"length": self.domain.x_end})
        profile = truncated.build()

        return profile


# --------------------------------------------------
# public API
# --------------------------------------------------
def load_body_fitted_config(path: str | Path) -> BodyFittedConfig:
    """Read and validate a body-fitted grid TOML file.

    A relative output filename is resolved against the folder holding the config file.

    Args:
        path: Configuration file.

    Returns:
        Validated configuration.

    Raises:
        OSError: If the file can't be read.
        tomllib.TOMLDecodeError: If the file isn't valid TOML.
        pydantic.ValidationError: If a value is missing, misspelled or out of range.
    """

    # convert to Path object
    path = Path(path)

    # read
    with path.open("rb") as stream:
        raw_dict = tomllib.load(stream)

    # validate
    config = BodyFittedConfig.model_validate(raw_dict)

    # resolve the output path relative to the config file
    output_file = path.parent / config.output.filename
    resolved_output = config.output.model_copy(update={"filename": output_file})
    resolved_config = config.model_copy(update={"output": resolved_output})

    return resolved_config


# --------------------------------------------------
# starter configuration
# --------------------------------------------------
BODY_FITTED_CONFIG_TEMPLATE = """\
# Generated by: grid-generator body-fitted init
# Edit this file, then run: grid-generator body-fitted run body_fitted.toml

# Body geometry, same contract as canonical-geometries (geometry plate|wedge|cone init).
# Stagnation point at the origin, x downstream, y up.
[geometry]
# type marker: "plate", "wedge" or "cone" (wedge and cone also need half_angle in [deg])
type = "plate"
# nose radius in [m]
nose_radius = 100.0e-6
# length of flat plate, measured from nose tip in [m]
length = 0.5

# Extent of the grid.
[domain]
# end of the grid along x, measured from nose tip in [m] (at most the geometry length)
x_end = 0.01
# constant wall-normal height of the grid in [m]; must clear the bow shock at x_end
# (for this Mach 6 plate case the shock is at about 2.8 mm at x = 10 mm)
height = 5.0e-3

# Point counts. Wall points: n_nose + n_body - 1 (nose and body share the junction).
[points]
# points on the nose arc, equally spaced in angle (polar block around the nose)
n_nose = 81
# points on the body; spacing grows geometrically from the nose spacing
n_body = 121
# points in the wall-normal direction
n_normal = 101
# first wall-normal spacing in [m]
first_normal_spacing = 1.0e-6

# The path is relative to this file.
[output]
# grid file; the extension picks the format via cfd-io (.su2, .h5, .p2dfmt, .msh, ...)
filename = "plate_local.su2"
# element order, for .msh only: 1 (straight-edged quads) or 2 (curved 9-node quads
# for high-order solvers; needs odd n_nose, n_body and n_normal)
order = 1
"""
