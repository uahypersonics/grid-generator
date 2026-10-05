"""Shared callbacks for the grid-generator CLI."""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
import typer

from grid_generator import __version__


# --------------------------------------------------
# callbacks
# --------------------------------------------------
def version_callback(value: bool) -> None:
    """Print the installed package version and exit."""

    if value:
        typer.echo(f"grid-generator {__version__}")
        raise typer.Exit()
