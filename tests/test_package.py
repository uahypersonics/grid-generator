"""Tests for the minimal public package scaffold."""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
from __future__ import annotations

import grid_generator


def test_package_exposes_version() -> None:
    """Expose package version metadata from the top-level package."""

    # validate version attribute
    assert isinstance(grid_generator.__version__, str)
    assert grid_generator.__version__