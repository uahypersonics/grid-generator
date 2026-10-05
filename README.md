# grid-generator

Structured grid generation utilities for Python.

[![PyPI](https://img.shields.io/pypi/v/grid-generator)](https://pypi.org/project/grid-generator/)
[![Docs](https://img.shields.io/badge/docs-zensical-blue)](https://uahypersonics.github.io/grid-generator/)
[![License](https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%E2%89%A53.11-blue.svg)](https://www.python.org/downloads/)

`grid-generator` builds structured computational grids and writes them through
the canonical `cfd-io` data model.

## Install

```bash
pip install grid-generator
```

## Quick Start

```bash
grid-generator cartesian init
grid-generator cartesian run cartesian.toml
```

The generated TOML file defines required `grid.x` and optional `grid.y` and
`grid.z` point distributions. Omitting optional axes creates singleton
dimensions, so Cartesian grids always use the structured `(ni, nj, nk)` array
contract.

The same workflow is available from Python:

```python
from grid_generator import generate_cartesian

dataset = generate_cartesian("cartesian.toml")
print(dataset.grid.shape)
```

## Features

- One-, two-, and three-dimensional Cartesian tensor-product grids
- Equidistant, geometric, tanh, and segmented point distributions
- Composable cubic and quintic transitions between equidistant regions
- Focused `cartesian init/run` CLI workflow
- HDF5 output through `cfd-io`
- Typed Python configuration and generation API

## Documentation

Documentation site: https://uahypersonics.github.io/grid-generator/

## Releasing

This project publishes to PyPI from Git tags that match `v*`.

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

The GitHub Actions publish workflow will build the package, run tests, and then
publish to PyPI using Trusted Publishing.

## License

GNU General Public License v3.0 or later. See [LICENSE](LICENSE) for the
complete license terms.
