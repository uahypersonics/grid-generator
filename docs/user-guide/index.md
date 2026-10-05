# User Guide

## Cartesian Grids

Create a starter configuration and generate its grid:

```bash
grid-generator cartesian init
grid-generator cartesian run cartesian.toml
```

The Cartesian config requires `[grid.x]`. The `[grid.y]` and `[grid.z]` tables
are optional:

| Defined axes | Grid shape |
|---|---|
| `x` | `(ni, 1, 1)` |
| `x`, `y` | `(ni, nj, 1)` |
| `x`, `y`, `z` | `(ni, nj, nk)` |

Each active axis uses the same one-dimensional distribution contract. Supported
types are `equidistant`, `geometric`, `tanh`, and `segmented`.

```toml
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

[output]
filename = "grid.hdf5"
dtype = "f8"
```

Artifact paths are resolved relative to the configuration file.

## Segmented Distributions

A segmented distribution begins with an equidistant region. Quintic regions
connect two equidistant regions while matching location, spacing, and zero
second derivative at both junctions. A cubic region may terminate the sequence
while matching location, spacing, and zero second derivative at its starting
junction.

The supported sequence is:

```text
equidistant (quintic equidistant)* [cubic]
```

This supports `1-3`, `1-5-1`, and repeated forms such as `1-5-1-5-1`:

```toml
[grid.x]
type = "segmented"
start = 0.0

[[grid.x.segments]]
type = "equidistant"
end = 0.1
spacing = 0.005

[[grid.x.segments]]
type = "quintic"
end = 0.4
n_points = 31

[[grid.x.segments]]
type = "equidistant"
end = 0.6
spacing = 0.01

[[grid.x.segments]]
type = "quintic"
end = 0.8
n_points = 21

[[grid.x.segments]]
type = "equidistant"
end = 1.0
spacing = 0.02
```

An equidistant segment accepts exactly one of `spacing` or `n_points`. Segment
point counts include both endpoints. Shared junction points are included once
in the assembled distribution.

For spacing-controlled equidistant regions, the region length must be exactly
divisible by the requested spacing. Invalid or non-monotone assembled grids are
rejected rather than adjusted silently.