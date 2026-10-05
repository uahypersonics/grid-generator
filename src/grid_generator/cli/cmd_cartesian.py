"""Cartesian-grid CLI commands."""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from grid_generator.cartesian import generate_cartesian
from grid_generator.config import CARTESIAN_CONFIG_TEMPLATE, load_cartesian_config

# --------------------------------------------------
# Cartesian command group
# --------------------------------------------------
cartesian_app = typer.Typer(
    name="cartesian",
    help="Generate Cartesian tensor-product grids.",
    no_args_is_help=True,
)


@cartesian_app.command("init")
def cmd_init(
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Configuration file to create."),
    ] = Path("cartesian.toml"),
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite an existing configuration."),
    ] = False,
) -> None:
    """Create a Cartesian-grid configuration."""

    # protect existing user configuration unless overwrite was requested
    if output.exists() and not force:
        typer.echo(f"Error: {output} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(code=1)

    # write and validate the starter configuration
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(CARTESIAN_CONFIG_TEMPLATE, encoding="utf-8")
    load_cartesian_config(output)

    typer.echo(f"Created: {output}")
    typer.echo(f"Edit the file, then run: grid-generator cartesian run {output}")


@cartesian_app.command("run")
def cmd_run(
    config: Annotated[
        Path,
        typer.Argument(help="Cartesian-grid TOML configuration."),
    ] = Path("cartesian.toml"),
) -> None:
    """Generate a Cartesian grid from a configuration."""

    try:
        from cfd_io import write_file

        cartesian_config = load_cartesian_config(config)
        dataset = generate_cartesian(cartesian_config)
        cartesian_config.output.parent.mkdir(parents=True, exist_ok=True)
        output_path = write_file(
            cartesian_config.output,
            dataset,
            dtype=cartesian_config.dtype,
        )
    except (ImportError, OSError, TypeError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from None

    typer.echo(f"Generated Cartesian grid: {dataset.grid.shape}")
    typer.echo(f"Wrote: {output_path}")
