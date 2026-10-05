"""Typed contracts for one-dimensional point distributions."""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


# --------------------------------------------------
# complete distributions
# --------------------------------------------------
@dataclass(frozen=True, slots=True)
class EquidistantSpec:
    """Equally spaced points between two endpoints."""

    start: float
    end: float
    n_points: int
    kind: Literal["equidistant"] = "equidistant"

    def __post_init__(self) -> None:
        """Validate the distribution bounds and point count."""

        _validate_interval(self.start, self.end, self.n_points)


@dataclass(frozen=True, slots=True)
class GeometricSpec:
    """Geometrically changing spacing between two endpoints."""

    start: float
    end: float
    n_points: int
    ratio: float | None = None
    first_spacing: float | None = None
    kind: Literal["geometric"] = "geometric"

    def __post_init__(self) -> None:
        """Validate the geometric-distribution parameters."""

        _validate_interval(self.start, self.end, self.n_points)
        parameters = (self.ratio is not None, self.first_spacing is not None)
        if sum(parameters) != 1:
            raise ValueError(
                "geometric distribution requires exactly one of ratio or first_spacing"
            )
        if self.ratio is not None and self.ratio <= 0.0:
            raise ValueError("geometric ratio must be greater than zero")
        if self.first_spacing is not None:
            length = self.end - self.start
            if not 0.0 < self.first_spacing < length:
                raise ValueError("geometric first_spacing must be between zero and the length")


@dataclass(frozen=True, slots=True)
class TanhSpec:
    """Hyperbolic-tangent point clustering at one or both endpoints."""

    start: float
    end: float
    n_points: int
    strength: float
    cluster: Literal["start", "end", "both"] = "start"
    kind: Literal["tanh"] = "tanh"

    def __post_init__(self) -> None:
        """Validate the tanh-distribution parameters."""

        _validate_interval(self.start, self.end, self.n_points)
        if self.strength <= 0.0:
            raise ValueError("tanh strength must be greater than zero")
        if self.cluster not in {"start", "end", "both"}:
            raise ValueError("tanh cluster must be 'start', 'end', or 'both'")


# --------------------------------------------------
# segmented distribution regions
# --------------------------------------------------
@dataclass(frozen=True, slots=True)
class EquidistantSegment:
    """One equidistant region ending at a specified coordinate."""

    end: float
    n_points: int | None = None
    spacing: float | None = None
    kind: Literal["equidistant"] = "equidistant"

    def __post_init__(self) -> None:
        """Require exactly one resolution control."""

        controls = (self.n_points is not None, self.spacing is not None)
        if sum(controls) != 1:
            raise ValueError("equidistant segment requires exactly one of n_points or spacing")
        if self.n_points is not None and self.n_points < 2:
            raise ValueError("equidistant segment n_points must be at least 2")
        if self.spacing is not None and self.spacing <= 0.0:
            raise ValueError("equidistant segment spacing must be greater than zero")


@dataclass(frozen=True, slots=True)
class CubicSegment:
    """Terminal cubic transition matching the incoming linear region."""

    end: float
    n_points: int
    kind: Literal["cubic"] = "cubic"

    def __post_init__(self) -> None:
        """Validate the transition point count."""

        if self.n_points < 2:
            raise ValueError("cubic segment n_points must be at least 2")


@dataclass(frozen=True, slots=True)
class QuinticSegment:
    """Quintic transition matching adjacent linear regions."""

    end: float
    n_points: int
    kind: Literal["quintic"] = "quintic"

    def __post_init__(self) -> None:
        """Validate the transition point count."""

        if self.n_points < 2:
            raise ValueError("quintic segment n_points must be at least 2")


SegmentSpec: TypeAlias = EquidistantSegment | CubicSegment | QuinticSegment


@dataclass(frozen=True, slots=True)
class SegmentedSpec:
    """Ordered linear and polynomial regions forming one distribution."""

    start: float
    segments: tuple[SegmentSpec, ...]
    kind: Literal["segmented"] = "segmented"

    def __post_init__(self) -> None:
        """Validate segment ordering and polynomial neighborhoods."""

        if not self.segments:
            raise ValueError("segmented distribution requires at least one segment")
        if not isinstance(self.segments[0], EquidistantSegment):
            raise ValueError("segmented distribution must begin with an equidistant segment")

        previous_end = self.start
        for index, segment in enumerate(self.segments):
            if segment.end <= previous_end:
                raise ValueError("segment endpoints must be strictly increasing")
            previous_end = segment.end

            if isinstance(segment, CubicSegment) and index != len(self.segments) - 1:
                raise ValueError("a cubic segment must be the final segment")
            if isinstance(segment, QuinticSegment):
                has_linear_neighbors = (
                    index > 0
                    and index + 1 < len(self.segments)
                    and isinstance(self.segments[index - 1], EquidistantSegment)
                    and isinstance(self.segments[index + 1], EquidistantSegment)
                )
                if not has_linear_neighbors:
                    raise ValueError("a quintic segment requires adjacent equidistant segments")

        for left, right in zip(self.segments, self.segments[1:], strict=False):
            if isinstance(left, EquidistantSegment) == isinstance(right, EquidistantSegment):
                raise ValueError("segmented regions must alternate between linear and polynomial")


DistributionSpec: TypeAlias = EquidistantSpec | GeometricSpec | TanhSpec | SegmentedSpec


# --------------------------------------------------
# shared validation
# --------------------------------------------------
def _validate_interval(start: float, end: float, n_points: int) -> None:
    """Validate common complete-distribution fields."""

    if n_points < 2:
        raise ValueError("distribution n_points must be at least 2")
    if end <= start:
        raise ValueError("distribution end must be greater than start")
