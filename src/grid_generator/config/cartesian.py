"""Configuration contract for Cartesian tensor-product grids."""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from grid_generator.distributions.models import DistributionSpec
from grid_generator.distributions.parse import parse_distribution


# --------------------------------------------------
# typed configuration
# --------------------------------------------------
@dataclass(frozen=True, slots=True)
class CartesianConfig:
    """Complete configuration for one Cartesian grid."""

    x: DistributionSpec
    output: Path
    y: DistributionSpec | None = None
    z: DistributionSpec | None = None
    dtype: str = "f8"

    def __post_init__(self) -> None:
        """Validate output options."""

        if self.dtype not in {"f4", "f8"}:
            raise ValueError("[output].dtype must be 'f4' or 'f8'")
        if self.output.suffix.lower() not in {".h5", ".hdf5"}:
            raise ValueError("[output].filename must use .h5 or .hdf5")


# --------------------------------------------------
# parser
# --------------------------------------------------
def load_cartesian_config(path: str | Path) -> CartesianConfig:
    """Read and validate a Cartesian-grid TOML configuration.

    Args:
        path: Configuration file path.

    Returns:
        Validated Cartesian configuration.
    """

    # read the TOML document
    path = Path(path)
    with path.open("rb") as stream:
        data = tomllib.load(stream)

    # validate top-level sections
    unknown_sections = sorted(set(data) - {"grid", "output"})
    if unknown_sections:
        unknown = ", ".join(unknown_sections)
        raise ValueError(f"unknown configuration sections: {unknown}")

    grid = data.get("grid")
    output = data.get("output")
    if not isinstance(grid, dict):
        raise TypeError("config must contain a [grid] table")
    if not isinstance(output, dict):
        raise TypeError("config must contain an [output] table")

    # validate this focused workflow and its axis sections
    unknown_grid_keys = sorted(set(grid) - {"type", "x", "y", "z"})
    if unknown_grid_keys:
        unknown = ", ".join(unknown_grid_keys)
        raise ValueError(f"unknown [grid] fields: {unknown}")
    if grid.get("type") != "cartesian":
        raise ValueError("[grid].type must be 'cartesian'")
    if "x" not in grid:
        raise ValueError("Cartesian grids require a [grid.x] table")

    unknown_output_keys = sorted(set(output) - {"filename", "dtype"})
    if unknown_output_keys:
        unknown = ", ".join(unknown_output_keys)
        raise ValueError(f"unknown [output] fields: {unknown}")

    # resolve output relative to the configuration file
    output_value = output.get("filename")
    if not isinstance(output_value, str) or not output_value.strip():
        raise ValueError("[output].filename must be a nonempty path string")
    output_path = Path(output_value)
    if not output_path.is_absolute():
        output_path = path.parent / output_path

    config = CartesianConfig(
        x=parse_distribution(grid["x"], "grid.x"),
        y=_parse_optional_axis(grid, "y"),
        z=_parse_optional_axis(grid, "z"),
        output=output_path,
        dtype=str(output.get("dtype", "f8")),
    )
    return config


def _parse_optional_axis(grid: dict[str, Any], name: str) -> DistributionSpec | None:
    """Parse an optional Cartesian axis."""

    axis = None
    if name in grid:
        axis = parse_distribution(grid[name], f"grid.{name}")
    return axis
