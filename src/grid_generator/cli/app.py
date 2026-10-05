"""Root application for the grid-generator CLI."""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
from typing import Annotated

import typer

from grid_generator.cli.callbacks import version_callback
from grid_generator.cli.cmd_cartesian import cartesian_app

# --------------------------------------------------
# root application
# --------------------------------------------------
app = typer.Typer(
    name="grid-generator",
    help="Generate structured computational grids.",
    no_args_is_help=True,
    add_completion=False,
)


# --------------------------------------------------
# register callbacks
# --------------------------------------------------
@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = False,
) -> None:
    """Generate structured computational grids."""

    del version


# --------------------------------------------------
# register subcommands
# --------------------------------------------------
app.add_typer(cartesian_app, name="cartesian")
