# grid-generator

`grid-generator` creates structured computational grids for CFD workflows.

The current Cartesian workflow generates one-, two-, or three-dimensional
tensor-product grids and writes canonical HDF5 datasets through `cfd-io`.

```bash
grid-generator cartesian init
grid-generator cartesian run cartesian.toml
```
