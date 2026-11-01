"""Write a 1D point distribution: Tecplot ASCII (.dat), CSV (.csv), or a bare column (.txt).

The .dat and .csv files hold one row per point with the columns

- i: point index, from 0
- x: coordinate [m]
- dx: spacing to the next point [m] (0 on the last point, which has no next point)
- ratio: dx divided by the previous point's dx (0 on the first and last point)

The .txt file holds only x, one value per line, no header (easy to read anywhere).
"""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

# --------------------------------------------------
# constants
# --------------------------------------------------
# full precision for the coordinates and spacings
_NUMBER_FORMAT = "{:.16e}"


# --------------------------------------------------
# public API
# --------------------------------------------------
def distribution_columns(coordinates: NDArray[np.float64]) -> dict[str, NDArray]:
    """Index, coordinate, spacing to the next point, and spacing ratio for each point.

    Args:
        coordinates: Points of the distribution, increasing.

    Returns:
        Columns "i", "x", "dx", "ratio", each with one entry per point.
    """

    # extract
    n_points = coordinates.size
    spacings = np.diff(coordinates)

    # spacing to the next point; the last point has none
    dx = np.zeros(n_points)
    dx[:-1] = spacings

    # growth of each spacing over the previous one; undefined on the first and last point
    ratio = np.zeros(n_points)
    ratio[1:-1] = spacings[1:] / spacings[:-1]

    columns = {
        "i": np.arange(n_points),
        "x": coordinates,
        "dx": dx,
        "ratio": ratio,
    }
    return columns


def write_distribution(coordinates: NDArray[np.float64], path: str | Path) -> Path:
    """Write the points to a file; the extension picks the format.

    Args:
        coordinates: Points of the distribution, increasing.
        path: Output file: .dat (Tecplot ASCII), .csv, or .txt (x only).

    Returns:
        The written path.

    Raises:
        ValueError: If no writer handles the extension.
    """

    # convert to Path object
    path = Path(path)

    # pick the writer
    extension = path.suffix.lower()
    if extension not in WRITERS:
        supported = ", ".join(WRITERS)
        raise ValueError(f"no distribution writer for '{path.suffix}'; supported: {supported}")
    writer = WRITERS[extension]

    # write
    writer(path, distribution_columns(coordinates))

    return path


# --------------------------------------------------
# writers, one per format
# --------------------------------------------------
def _write_tecplot(path: Path, columns: dict[str, NDArray]) -> None:
    """Tecplot ASCII: one I-ordered zone, one row per point."""

    # header
    names = ", ".join(f'"{name}"' for name in columns)
    n_points = columns["x"].size
    lines = [
        'TITLE = "distribution"',
        f"VARIABLES = {names}",
        f'ZONE T="distribution", I={n_points}, F=POINT',
    ]

    # rows
    for row in range(n_points):
        lines.append(_format_row(columns, row, separator=" "))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(path: Path, columns: dict[str, NDArray]) -> None:
    """CSV with a header row."""

    # header, then rows
    lines = [",".join(columns)]
    for row in range(columns["x"].size):
        lines.append(_format_row(columns, row, separator=","))

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_column(path: Path, columns: dict[str, NDArray]) -> None:
    """Bare x column: one value per line, no header."""

    # x only
    lines = [_NUMBER_FORMAT.format(value) for value in columns["x"]]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_row(columns: dict[str, NDArray], row: int, separator: str) -> str:
    """One row: the index as an integer, the other columns in full precision."""

    # build
    fields = [str(int(columns["i"][row]))]
    for name in ("x", "dx", "ratio"):
        fields.append(_NUMBER_FORMAT.format(columns[name][row]))
    line = separator.join(fields)

    return line


# --------------------------------------------------
# registry: extension -> writer
# --------------------------------------------------
WRITERS: dict[str, Callable[[Path, dict[str, NDArray]], None]] = {
    ".dat": _write_tecplot,
    ".csv": _write_csv,
    ".txt": _write_column,
}
