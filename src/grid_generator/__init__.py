"""Public package interface for grid_generator."""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
from importlib.metadata import PackageNotFoundError, version


# --------------------------------------------------
# resolve package version
# --------------------------------------------------
try:
    __version__ = version("grid-generator")
except PackageNotFoundError:
    __version__ = "0+unknown"


__all__ = ["__version__"]