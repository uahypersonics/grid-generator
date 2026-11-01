"""Configuration contract for 1D point distributions: a [distribution] table and the [output] file.

The [distribution] table takes the same types and keys as a Cartesian axis
(`grid-generator distribution info` lists them). The config is parsed and validated
with pydantic; the writer works from the validated object.
"""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from grid_generator.config.points import parse_table
from grid_generator.distributions.models import DistributionSpec
from grid_generator.distributions.writers import WRITERS


# --------------------------------------------------
# table parsing
# --------------------------------------------------
def _parse_distribution_table(value: object) -> object:
    """Turn a raw [distribution] table into a distribution spec."""

    # tables come from TOML; anything else (an existing spec) passes through
    distribution = value
    if isinstance(value, dict):
        distribution = parse_table(value, "distribution")

    return distribution


# --------------------------------------------------
# tables
# --------------------------------------------------
class DistributionOutputConfig(BaseModel):
    """Point file; a relative path is resolved against the config file's folder."""

    # reject misspelled keys
    model_config = ConfigDict(extra="forbid")

    filename: Path = Field(description="Point file: .dat (Tecplot ASCII), .csv, or .txt (x only)")

    @field_validator("filename")
    @classmethod
    def _check_extension(cls, filename: Path) -> Path:
        """Reject extensions without a writer, so the error comes before any work."""

        # check against the writer registry
        extension = filename.suffix.lower()
        if extension not in WRITERS:
            supported = ", ".join(WRITERS)
            raise ValueError(
                f"[output] no distribution writer for '{filename.suffix}'; supported: {supported}"
            )

        return filename


# --------------------------------------------------
# whole file
# --------------------------------------------------
class DistributionFileConfig(BaseModel):
    """Contents of a 1D distribution TOML file."""

    # reject unknown sections
    model_config = ConfigDict(extra="forbid")

    distribution: Annotated[DistributionSpec, BeforeValidator(_parse_distribution_table)]
    output: DistributionOutputConfig


# --------------------------------------------------
# public API
# --------------------------------------------------
def load_distribution_config(path: str | Path) -> DistributionFileConfig:
    """Read and validate a 1D distribution TOML file.

    A relative output filename is resolved against the folder holding the config file.

    Args:
        path: Configuration file.

    Returns:
        Validated configuration.

    Raises:
        OSError: If the file can't be read.
        tomllib.TOMLDecodeError: If the file isn't valid TOML.
        pydantic.ValidationError: If a value is missing, misspelled or out of range.
    """

    # convert to Path object
    path = Path(path)

    # read
    with path.open("rb") as stream:
        raw_dict = tomllib.load(stream)

    # validate
    config = DistributionFileConfig.model_validate(raw_dict)

    # resolve the output path relative to the config file
    output_file = path.parent / config.output.filename
    resolved_output = config.output.model_copy(update={"filename": output_file})
    resolved_config = config.model_copy(update={"output": resolved_output})

    return resolved_config
