"""Configuration contracts for grid-generator workflows."""

from grid_generator.config.cartesian import (
    CARTESIAN_CONFIG_TEMPLATE,
    CartesianConfig,
    load_cartesian_config,
)
from grid_generator.distributions import DistributionSpec

__all__ = [
    "CARTESIAN_CONFIG_TEMPLATE",
    "CartesianConfig",
    "DistributionSpec",
    "load_cartesian_config",
]
