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

## Body-Fitted Grids

Body-fitted 2D grids wrap a blunt body: a blunted flat plate, a blunted wedge,
or a sphere-cone meridian. Create the starter configuration (the local Mach 6
blunted-plate case) and generate its grid:

```bash
grid-generator body-fitted init
grid-generator body-fitted run body_fitted.toml
```

The `[geometry]` table is the same as in
[canonical-geometries](https://github.com/uahypersonics/canonical-geometries)
(`geometry plate|wedge|cone init`), so one geometry definition works in both
tools. The stagnation point is at the origin, x runs downstream and y up.

```toml
[geometry]
type = "plate"
nose_radius = 100.0e-6
length = 0.5

[domain]
x_end = 0.01
height = 5.0e-3

[points]
n_nose = 81
n_body = 121
n_normal = 101
first_normal_spacing = 1.0e-6

[output]
filename = "plate_local.su2"
order = 1
```

The grid layout:

- **i along the wall**, from the stagnation point around the nose to `x_end`.
  Nose points are equally spaced in angle up to the tangency point, so the nose
  block is polar about the nose centre. Along the body the spacing grows
  geometrically, starting from the nose spacing. The nose and the body share the
  junction point, so there are `n_nose + n_body - 1` wall points.
- **j away from the wall**: every j-line runs straight out along the exact wall
  normal, from the wall to the same height `height`, with geometric growth from
  `first_normal_spacing`. The j-lines are orthogonal to the wall by construction.
- **Boundary markers** for SU2 output: `imin` symmetry (the stagnation line),
  `imax` outflow, `jmin` wall, `jmax` farfield.

`run` prints a quality report: smallest cell area (positive means every cell is
valid and counter-clockwise), the largest ratio of neighbouring cell sizes along
i and along j, and the largest wall skew.

There is no shock alignment yet, and the height is constant: choose `height`
large enough to clear the bow shock at `x_end`. Two consequences of this simple
layout:

- Near the nose the shock sits close to the wall compared with `height`, so it
  is resolved by few cells there.
- The nose block fans out while the body's j-lines are parallel. Away from the
  wall, cell width along i jumps across the junction line, by up to
  `(nose_radius + height) / nose_radius` at the outer boundary. The quality
  report shows this as the largest spacing ratio along i.

The output format follows the file extension, through cfd-io: `.su2` for SU2,
`.p2dfmt` for ASCII Plot3D, `.msh` for Gmsh, `.h5` for HDF5 (the
boundary markers are stored with the grid).

For `.msh`, `order` in `[output]` picks the element type, which the extension
can't express:

```toml
[output]
filename = "plate_local.msh"
order = 2
```

- `order = 1` (default): one straight-edged 4-node quad per grid cell.
- `order = 2`: one 9-node quad per 2 x 2 grid cells. Its edges are parabolas
  through three grid points, so the nose stays curved, which high-order solvers
  need. Requires odd `n_nose`, `n_body` and `n_normal`; the odd
  `n_nose` puts the nose/body junction, where the wall curvature jumps, on an
  element corner instead of inside an element.

`order = 2` with any other extension is rejected.

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