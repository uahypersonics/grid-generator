"""Public package interface for grid_generator."""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
from importlib.metadata import (
    PackageNotFoundError,
    version,
)

from grid_generator.cartesian import generate_cartesian
from grid_generator.config import CartesianConfig, load_cartesian_config
from grid_generator.distributions import (
    CubicSegment,
    DistributionSpec,
    EquidistantSegment,
    EquidistantSpec,
    GeometricSpec,
    QuinticSegment,
    SegmentedSpec,
    TanhSpec,
    build_distribution,
)

# --------------------------------------------------
# resolve package version
# --------------------------------------------------
try:
    __version__ = version("grid-generator")
except PackageNotFoundError:
    __version__ = "0+unknown"


__all__ = [
    "CubicSegment",
    "CartesianConfig",
    "DistributionSpec",
    "EquidistantSegment",
    "EquidistantSpec",
    "GeometricSpec",
    "QuinticSegment",
    "SegmentedSpec",
    "TanhSpec",
    "__version__",
    "build_distribution",
    "generate_cartesian",
    "load_cartesian_config",
]
