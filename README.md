# grid-generator

Structured grid generation utilities for Python.

[![PyPI](https://img.shields.io/pypi/v/grid-generator)](https://pypi.org/project/grid-generator/)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue)](https://uahypersonics.github.io/grid-generator/)
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-%E2%89%A53.11-blue.svg)](https://www.python.org/downloads/)

`grid-generator` is a lightweight Python package for building simple structured
grids. This repository currently contains the initial public scaffold: package
layout, documentation, and release automation.

## Install

```bash
pip install grid-generator
```

## Quick Start

```python
from grid_generator import __version__

print(__version__)
```

## Features

- Minimal Python package scaffold based on the structure used in `flow-state`
- and `cfd-io`
- Minimal public package with only `src/grid_generator/__init__.py`
- MkDocs documentation scaffold with API reference pages
- GitHub Actions workflows for documentation deployment and tag-based PyPI
	publishing via Trusted Publishing

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

BSD-3-Clause. See [LICENSE](LICENSE) for details.
