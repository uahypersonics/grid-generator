"""Assembly of equidistant and polynomial distribution segments."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from grid_generator.distributions.models import (
    CubicSegment,
    EquidistantSegment,
    SegmentedSpec,
)
from grid_generator.distributions.polynomial import (
    build_cubic_transition,
    build_quintic_transition,
)


def build_segmented(spec: SegmentedSpec) -> NDArray[np.float64]:
    """Build and join an ordered sequence of linear and polynomial regions."""

    arrays: list[NDArray[np.float64]] = []
    segment_start = spec.start

    for index, segment in enumerate(spec.segments):
        if isinstance(segment, EquidistantSegment):
            coordinates, _ = _build_equidistant_segment(segment_start, segment)
        elif isinstance(segment, CubicSegment):
            start_spacing = float(arrays[-1][-1] - arrays[-1][-2])
            coordinates = build_cubic_transition(
                segment_start,
                segment.end,
                segment.n_points,
                start_spacing,
            )
        else:
            start_spacing = float(arrays[-1][-1] - arrays[-1][-2])
            next_segment = spec.segments[index + 1]
            if not isinstance(next_segment, EquidistantSegment):
                raise TypeError("quintic segment must be followed by an equidistant segment")
            end_spacing = _equidistant_spacing(segment.end, next_segment)
            coordinates = build_quintic_transition(
                segment_start,
                segment.end,
                segment.n_points,
                start_spacing,
                end_spacing,
            )

        arrays.append(coordinates)
        segment_start = segment.end

    joined = arrays[0]
    for coordinates in arrays[1:]:
        joined = np.concatenate((joined, coordinates[1:]))
    return joined


def _build_equidistant_segment(
    start: float,
    segment: EquidistantSegment,
) -> tuple[NDArray[np.float64], float]:
    """Build one linear region and return its exact spacing."""

    spacing = _equidistant_spacing(start, segment)
    if segment.n_points is not None:
        n_points = segment.n_points
    else:
        n_intervals = round((segment.end - start) / spacing)
        n_points = n_intervals + 1

    coordinates = np.linspace(start, segment.end, n_points)
    return coordinates, spacing


def _equidistant_spacing(start: float, segment: EquidistantSegment) -> float:
    """Resolve one linear region's spacing and enforce exact divisibility."""

    length = segment.end - start
    if segment.n_points is not None:
        spacing = length / (segment.n_points - 1)
        return spacing

    spacing = float(segment.spacing)
    interval_count = length / spacing
    nearest_count = round(interval_count)
    if nearest_count < 1 or not np.isclose(interval_count, nearest_count, rtol=1.0e-10):
        raise ValueError("equidistant segment length must be divisible by spacing")
    return spacing
