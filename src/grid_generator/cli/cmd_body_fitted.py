"""Body-fitted-grid CLI commands."""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Annotated

import typer

from grid_generator.body_fitted import generate_body_fitted
from grid_generator.config import BODY_FITTED_CONFIG_TEMPLATE, load_body_fitted_config
from grid_generator.quality import grid_quality

# --------------------------------------------------
# body-fitted command group
# --------------------------------------------------
body_fitted_app = typer.Typer(
    name="body-fitted",
    help="Generate constant-height body-fitted 2D grids around blunt bodies.",
    no_args_is_help=True,
)


@body_fitted_app.command("init")
def cmd_init(
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Configuration file to create."),
    ] = Path("body_fitted.toml"),
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite an existing configuration."),
    ] = False,
) -> None:
    """Create a body-fitted-grid configuration."""

    # protect existing user configuration unless overwrite was requested
    if output.exists() and not force:
        typer.echo(f"Error: {output} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(code=1)

    # write and validate the starter configuration
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(BODY_FITTED_CONFIG_TEMPLATE, encoding="utf-8")
    load_body_fitted_config(output)

    typer.echo(f"Created: {output}")
    typer.echo(f"Edit the file, then run: grid-generator body-fitted run {output}")


@body_fitted_app.command("run")
def cmd_run(
    config: Annotated[
        Path,
        typer.Argument(help="Body-fitted-grid TOML configuration."),
    ] = Path("body_fitted.toml"),
) -> None:
    """Generate a body-fitted grid from a configuration."""

    try:
        from cfd_io import write_file
        from cfd_io.writers.gmsh import write_gmsh

        # read and validate (pydantic's ValidationError is a ValueError)
        body_fitted_config = load_body_fitted_config(config)

        # generate and measure
        dataset = generate_body_fitted(body_fitted_config)
        quality = grid_quality(dataset.grid)

        # write: Gmsh gets the element order, which the file extension can't carry;
        # everything else by extension, in double precision (cfd-io's HDF5 default is float32)
        output_file = body_fitted_config.output.filename
        output_file.parent.mkdir(parents=True, exist_ok=True)
        if output_file.suffix.lower() == ".msh":
            output_path = write_gmsh(output_file, dataset, order=body_fitted_config.output.order)
        else:
            output_path = write_file(output_file, dataset, dtype="f8")
    except (ImportError, OSError, TypeError, ValueError, tomllib.TOMLDecodeError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None

    # report
    ni, nj, _ = dataset.grid.shape
    typer.echo(f"Generated body-fitted grid: {ni} x {nj} points ({ni - 1} x {nj - 1} cells)")
    typer.echo(quality.summary())
    typer.echo(f"Wrote: {output_path}")
