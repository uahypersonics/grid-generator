"""Configuration contract for Cartesian tensor-product grids."""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from grid_generator.distributions.models import (
    CubicSegment,
    DistributionSpec,
    EquidistantSegment,
    EquidistantSpec,
    GeometricSpec,
    QuinticSegment,
    SegmentedSpec,
    SegmentSpec,
    TanhSpec,
)


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
        x=_parse_axis(grid["x"], "x"),
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
        axis = _parse_axis(grid[name], name)
    return axis


def _parse_axis(value: Any, name: str) -> DistributionSpec:
    """Parse and validate one Cartesian axis table."""

    if not isinstance(value, dict):
        raise TypeError(f"[grid.{name}] must be a table")

    kind = str(value.get("type", "equidistant"))
    if kind == "segmented":
        axis = _parse_segmented(value, name)
    else:
        axis = _parse_complete_distribution(value, name, kind)
    return axis


def _parse_complete_distribution(
    value: dict[str, Any],
    name: str,
    kind: str,
) -> DistributionSpec:
    """Parse an equidistant, geometric, or tanh axis."""

    common_keys = {"type", "start", "end", "n_points"}
    kind_keys = {
        "equidistant": set(),
        "geometric": {"ratio", "first_spacing"},
        "tanh": {"strength", "cluster"},
    }
    if kind not in kind_keys:
        valid = ", ".join((*kind_keys, "segmented"))
        raise ValueError(f"[grid.{name}].type must be one of: {valid}")

    allowed_keys = common_keys | kind_keys[kind]
    unknown_keys = sorted(set(value) - allowed_keys)
    if unknown_keys:
        unknown = ", ".join(unknown_keys)
        raise ValueError(f"unknown [grid.{name}] fields: {unknown}")

    required_keys = {"start", "end", "n_points"}
    missing_keys = sorted(required_keys - set(value))
    if missing_keys:
        missing = ", ".join(missing_keys)
        raise ValueError(f"[grid.{name}] is missing fields: {missing}")

    common = {
        "start": float(value["start"]),
        "end": float(value["end"]),
        "n_points": int(value["n_points"]),
    }
    if kind == "equidistant":
        distribution: DistributionSpec = EquidistantSpec(**common)
    elif kind == "geometric":
        ratio = value.get("ratio")
        first_spacing = value.get("first_spacing")
        distribution = GeometricSpec(
            **common,
            ratio=float(ratio) if ratio is not None else None,
            first_spacing=float(first_spacing) if first_spacing is not None else None,
        )
    else:
        if "strength" not in value:
            raise ValueError(f"[grid.{name}] is missing fields: strength")
        distribution = TanhSpec(
            **common,
            strength=float(value["strength"]),
            cluster=str(value.get("cluster", "start")),
        )
    return distribution


def _parse_segmented(value: dict[str, Any], name: str) -> SegmentedSpec:
    """Parse an ordered segmented distribution."""

    allowed_keys = {"type", "start", "segments"}
    unknown_keys = sorted(set(value) - allowed_keys)
    if unknown_keys:
        unknown = ", ".join(unknown_keys)
        raise ValueError(f"unknown [grid.{name}] fields: {unknown}")
    if "start" not in value:
        raise ValueError(f"[grid.{name}] is missing fields: start")

    raw_segments = value.get("segments")
    if not isinstance(raw_segments, list):
        raise TypeError(f"[[grid.{name}.segments]] must define a list of tables")

    segments = tuple(
        _parse_segment(segment, name, index) for index, segment in enumerate(raw_segments)
    )
    distribution = SegmentedSpec(start=float(value["start"]), segments=segments)
    return distribution


def _parse_segment(value: Any, axis_name: str, index: int) -> SegmentSpec:
    """Parse one linear or polynomial segment table."""

    label = f"grid.{axis_name}.segments[{index}]"
    if not isinstance(value, dict):
        raise TypeError(f"[{label}] must be a table")

    kind = value.get("type")
    common_keys = {"type", "end", "n_points"}
    if kind == "equidistant":
        allowed_keys = common_keys | {"spacing"}
    elif kind in {"cubic", "quintic"}:
        allowed_keys = common_keys
    else:
        raise ValueError(f"[{label}].type must be 'equidistant', 'cubic', or 'quintic'")

    unknown_keys = sorted(set(value) - allowed_keys)
    if unknown_keys:
        unknown = ", ".join(unknown_keys)
        raise ValueError(f"unknown [{label}] fields: {unknown}")
    if "end" not in value:
        raise ValueError(f"[{label}] is missing fields: end")

    end = float(value["end"])
    n_points = value.get("n_points")
    if kind == "equidistant":
        spacing = value.get("spacing")
        segment: SegmentSpec = EquidistantSegment(
            end=end,
            n_points=int(n_points) if n_points is not None else None,
            spacing=float(spacing) if spacing is not None else None,
        )
    elif kind == "cubic":
        if n_points is None:
            raise ValueError(f"[{label}] is missing fields: n_points")
        segment = CubicSegment(end=end, n_points=int(n_points))
    else:
        if n_points is None:
            raise ValueError(f"[{label}] is missing fields: n_points")
        segment = QuinticSegment(end=end, n_points=int(n_points))
    return segment


# --------------------------------------------------
# starter configuration
# --------------------------------------------------
CARTESIAN_CONFIG_TEMPLATE = """\
# Generated by: grid-generator cartesian init
# Edit this file, then run: grid-generator cartesian run cartesian.toml

[grid]
type = "cartesian"

[grid.x]
type = "equidistant"
start = 0.1
end = 1.0
n_points = 10

[grid.y]
type = "geometric"
start = 0.0
end = 0.05
n_points = 100
first_spacing = 1.0e-6

# Segmented axes compose equidistant and polynomial regions. For example:
# [grid.x]
# type = "segmented"
# start = 0.0
#
# [[grid.x.segments]]
# type = "equidistant"
# end = 0.1
# spacing = 0.005
#
# [[grid.x.segments]]
# type = "quintic"
# end = 0.4
# n_points = 31
#
# [[grid.x.segments]]
# type = "equidistant"
# end = 1.0
# spacing = 0.01

# Uncomment to create a three-dimensional grid.
# [grid.z]
# type = "equidistant"
# start = -0.1
# end = 0.1
# n_points = 20

[output]
filename = "grid.hdf5"
dtype = "f8"
"""
