"""Tests for constant-height body-fitted grids, their configuration, and the CLI."""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
from cfd_io import read_file
from typer.testing import CliRunner

from grid_generator import (
    BodyFittedConfig,
    generate_body_fitted,
    grid_quality,
    load_body_fitted_config,
)
from grid_generator.body_fitted import BOUNDARY_MARKERS
from grid_generator.cli import app
from grid_generator.config import BODY_FITTED_CONFIG_TEMPLATE

runner = CliRunner()

# the template's local plate case
NOSE_RADIUS = 100.0e-6
X_END = 0.01
HEIGHT = 5.0e-3
N_NOSE = 81
N_BODY = 121
N_NORMAL = 101
FIRST_NORMAL_SPACING = 1.0e-6


def write_config(tmp_path: Path, old: str = "", new: str = "") -> Path:
    """Write the starter template, optionally with one replacement, and return its path."""

    # build the config text
    config_text = BODY_FITTED_CONFIG_TEMPLATE
    if old:
        assert old in config_text
        config_text = config_text.replace(old, new, 1)

    # write
    config_path = tmp_path / "body_fitted.toml"
    config_path.write_text(config_text)

    return config_path


@pytest.fixture
def plate_config(tmp_path: Path) -> BodyFittedConfig:
    """The template's 10 mm local plate grid."""
    return load_body_fitted_config(write_config(tmp_path))


@pytest.fixture
def cone_config(tmp_path: Path) -> BodyFittedConfig:
    """A 7 deg cone on the same grid settings."""
    config_path = write_config(tmp_path, 'type = "plate"', 'type = "cone"\nhalf_angle = 7.0')
    return load_body_fitted_config(config_path)


def wall_distances(config: BodyFittedConfig, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Distance of each grid point from the wall along the matching wall normal."""

    # wall points and normals, one per i
    profile = config.build_profile()
    x_wall = x[:, 0]
    y_wall = y[:, 0]
    s_wall = np.zeros_like(x_wall)

    # recover s from the wall points (nose: polar angle, body: distance from the junction)
    s_junction = profile.junction_arc_length
    x_j, y_j = profile.junction_point
    on_nose = np.arange(x_wall.size) < N_NOSE
    s_wall[on_nose] = NOSE_RADIUS * np.arctan2(y_wall[on_nose], NOSE_RADIUS - x_wall[on_nose])
    s_wall[~on_nose] = s_junction + np.hypot(x_wall[~on_nose] - x_j, y_wall[~on_nose] - y_j)
    nx, ny = profile.normal(s_wall)

    # projection of each point's offset from its wall point onto the normal
    distance = (x - x_wall[:, None]) * nx[:, None] + (y - y_wall[:, None]) * ny[:, None]

    return distance


# --------------------------------------------------
# grid layout
# --------------------------------------------------
def test_shape_and_markers(plate_config: BodyFittedConfig) -> None:
    """201 x 101 points (200 x 100 cells), 2D, with the four SU2 boundary markers."""

    # build
    dataset = generate_body_fitted(plate_config)

    # check
    assert dataset.grid.shape == (N_NOSE + N_BODY - 1, N_NORMAL, 1)
    assert dataset.attrs["markers"]["structured"] == BOUNDARY_MARKERS
    assert dataset.attrs["geometry_type"] == "plate"
    assert dataset.attrs["axisymmetric"] is False
    np.testing.assert_array_equal(dataset.grid.z, 0.0)


@pytest.mark.parametrize("config_name", ["plate_config", "cone_config"])
def test_wall_points_lie_on_the_profile(config_name: str, request) -> None:
    """j = 0 starts at the stagnation point, ends at x_end, and stays on the exact profile."""

    # build
    config = request.getfixturevalue(config_name)
    grid = generate_body_fitted(config).grid
    x_wall = grid.x[:, 0, 0]
    y_wall = grid.y[:, 0, 0]

    # check the ends
    assert (x_wall[0], y_wall[0]) == (0.0, 0.0)
    assert x_wall[-1] == pytest.approx(X_END, rel=1e-14)

    # check the nose points sit on the circle and the body points on the body line
    profile = config.build_profile()
    radius = np.hypot(x_wall[:N_NOSE] - NOSE_RADIUS, y_wall[:N_NOSE])
    np.testing.assert_allclose(radius, NOSE_RADIUS, rtol=1e-12)
    theta = math.radians(profile.half_angle)
    x_j, y_j = profile.junction_point
    off_line = -(x_wall[N_NOSE:] - x_j) * math.sin(theta) + (y_wall[N_NOSE:] - y_j) * math.cos(
        theta
    )
    np.testing.assert_allclose(off_line, 0.0, atol=1e-15)


@pytest.mark.parametrize("config_name", ["plate_config", "cone_config"])
def test_j_lines_are_wall_normals_of_constant_height(config_name: str, request) -> None:
    """Every j-line runs along its exact wall normal, and the outer boundary is at height H."""

    # build
    config = request.getfixturevalue(config_name)
    grid = generate_body_fitted(config).grid
    x = grid.x[:, :, 0]
    y = grid.y[:, :, 0]

    # distance along the normal, and the full offset from the wall point
    normal_distance = wall_distances(config, x, y)
    offset = np.hypot(x - x[:, :1], y - y[:, :1])

    # check: offsets are purely along the normal, and j = jmax is at H everywhere
    np.testing.assert_allclose(normal_distance, offset, atol=1e-15)
    np.testing.assert_allclose(normal_distance[:, -1], HEIGHT, rtol=1e-12)
    assert offset[0, 1] == pytest.approx(FIRST_NORMAL_SPACING, rel=1e-8)


def test_nose_is_a_polar_block(plate_config: BodyFittedConfig) -> None:
    """Nose wall points are equally spaced in angle from 0 to 90 deg; nose j-lines are radial."""

    # build
    grid = generate_body_fitted(plate_config).grid
    x_nose = grid.x[:N_NOSE, :, 0]
    y_nose = grid.y[:N_NOSE, :, 0]

    # polar angle of every nose point about the nose centre
    phi = np.arctan2(y_nose, NOSE_RADIUS - x_nose)

    # check: equal angle steps along i, constant angle along each j-line
    expected = np.linspace(0.0, 0.5 * math.pi, N_NOSE)
    np.testing.assert_allclose(phi[:, 0], expected, atol=1e-12)
    np.testing.assert_allclose(phi, np.broadcast_to(phi[:, :1], phi.shape), atol=1e-12)


def test_wall_spacing_is_continuous_at_the_junction(plate_config: BodyFittedConfig) -> None:
    """The first body spacing equals the nose spacing, and the body spacing then grows."""

    # wall spacings in arc length (chord lengths on the nose, exact on the body)
    grid = generate_body_fitted(plate_config).grid
    wall_spacing = np.hypot(np.diff(grid.x[:, 0, 0]), np.diff(grid.y[:, 0, 0]))

    # nose arc spacing (chord of one angle step)
    angle_step = 0.5 * math.pi / (N_NOSE - 1)
    nose_chord = 2.0 * NOSE_RADIUS * math.sin(0.5 * angle_step)
    nose_arc = NOSE_RADIUS * angle_step

    # check
    np.testing.assert_allclose(wall_spacing[: N_NOSE - 1], nose_chord, rtol=1e-10)
    assert wall_spacing[N_NOSE - 1] == pytest.approx(nose_arc, rel=1e-8)
    assert np.all(np.diff(wall_spacing[N_NOSE - 1 :]) > 0.0)


@pytest.mark.parametrize("config_name", ["plate_config", "cone_config"])
def test_all_cells_valid_and_counter_clockwise(config_name: str, request) -> None:
    """Every cell has positive area with corners counter-clockwise in (i, j)."""

    # build and measure
    config = request.getfixturevalue(config_name)
    quality = grid_quality(generate_body_fitted(config).grid)

    # check
    assert quality.min_cell_area > 0.0
    assert quality.max_spacing_ratio_j < 1.1


# --------------------------------------------------
# configuration
# --------------------------------------------------
@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("x_end = 0.01", "x_end = 0.6", "must not exceed"),
        ("x_end = 0.01", "x_end = 50.0e-6", "must reach past the nose"),
        ("first_normal_spacing = 1.0e-6", "first_normal_spacing = 1.0e-2", "smaller than"),
        ("n_nose = 81", "n_nose = 1", "n_nose"),
        ("height = 5.0e-3", "hieght = 5.0e-3", "hieght"),
        ('type = "plate"', 'type = "cone"', "half_angle"),
    ],
)
def test_load_rejects_bad_config(tmp_path: Path, old: str, new: str, message: str) -> None:
    """x_end outside the body, a too-large first spacing, bad counts and keys raise."""

    # write a broken config
    config_path = write_config(tmp_path, old, new)

    with pytest.raises(ValueError, match=message):
        load_body_fitted_config(config_path)


def write_order_2_config(tmp_path: Path, old: str = "", new: str = "") -> Path:
    """Write the template as a second-order .msh config, optionally with one more replacement."""

    # Gmsh output, second order
    config_text = BODY_FITTED_CONFIG_TEMPLATE
    config_text = config_text.replace(
        'filename = "plate_local.su2"', 'filename = "plate_local.msh"'
    )
    config_text = config_text.replace("order = 1", "order = 2")

    # optional extra change
    if old:
        assert old in config_text
        config_text = config_text.replace(old, new, 1)

    # write
    config_path = tmp_path / "body_fitted.toml"
    config_path.write_text(config_text)

    return config_path


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ('filename = "plate_local.msh"', 'filename = "plate_local.su2"', "needs a .msh filename"),
        ("n_nose = 81", "n_nose = 80", "n_nose = 80"),
        ("n_body = 121", "n_body = 120", "n_body = 120"),
        ("n_normal = 101", "n_normal = 100", "n_normal = 100"),
        ("order = 2", "order = 3", "order"),
    ],
)
def test_load_rejects_bad_order(tmp_path: Path, old: str, new: str, message: str) -> None:
    """Order 2 needs .msh output and odd point counts (junction on an element corner)."""

    # write a broken config
    config_path = write_order_2_config(tmp_path, old, new)

    with pytest.raises(ValueError, match=message):
        load_body_fitted_config(config_path)


def test_load_keeps_the_order(tmp_path: Path) -> None:
    """Resolving the output path keeps the rest of [output]."""

    # check
    config = load_body_fitted_config(write_order_2_config(tmp_path))
    assert config.output.order == 2
    assert config.output.filename == tmp_path / "plate_local.msh"


def test_load_resolves_output_next_to_the_config(
    plate_config: BodyFittedConfig, tmp_path: Path
) -> None:
    """A relative output filename is resolved against the config file's folder."""

    # check
    assert plate_config.output.filename == tmp_path / "plate_local.su2"


# --------------------------------------------------
# CLI end to end
# --------------------------------------------------
def test_cli_init_then_run_writes_su2(tmp_path: Path) -> None:
    """body-fitted init + run writes an SU2 grid with the right size and four markers."""

    # init and run
    config_path = tmp_path / "body_fitted.toml"
    result_init = runner.invoke(app, ["body-fitted", "init", "--output", str(config_path)])
    result_run = runner.invoke(app, ["body-fitted", "run", str(config_path)])

    # check the commands and the report
    assert result_init.exit_code == 0, result_init.output
    assert result_run.exit_code == 0, result_run.output
    assert "200 x 100 cells" in result_run.output
    assert "smallest cell area" in result_run.output

    # check the file: sizes and marker names in the SU2 header blocks
    su2_text = (tmp_path / "plate_local.su2").read_text()
    assert "NDIME= 2" in su2_text
    assert "NELEM= 20000" in su2_text
    assert "NPOIN= 20301" in su2_text
    for marker in BOUNDARY_MARKERS.values():
        assert f"MARKER_TAG= {marker}" in su2_text


def test_cli_su2_reads_back_with_the_same_points(tmp_path: Path) -> None:
    """cfd-io reads the SU2 file back with the generated wall and outer points."""

    # init and run
    config_path = tmp_path / "body_fitted.toml"
    runner.invoke(app, ["body-fitted", "init", "--output", str(config_path)])
    runner.invoke(app, ["body-fitted", "run", str(config_path)])

    # read back and compare point clouds (SU2 is unstructured, so compare sorted coordinates)
    expected = generate_body_fitted(config_path).grid
    written = read_file(tmp_path / "plate_local.su2", orient=False)
    expected_points = np.column_stack([expected.x.ravel(), expected.y.ravel()])
    written_points = np.column_stack([np.ravel(written.grid.x), np.ravel(written.grid.y)])
    expected_sorted = expected_points[np.lexsort(expected_points.T)]
    written_sorted = written_points[np.lexsort(written_points.T)]
    np.testing.assert_allclose(written_sorted, expected_sorted, rtol=1e-12, atol=1e-18)


def test_cli_hdf5_keeps_points_and_markers(tmp_path: Path) -> None:
    """HDF5 output reads back with the same structured points and the boundary markers."""

    # config writing HDF5 instead of SU2
    config_path = write_config(tmp_path, "plate_local.su2", "plate_local.h5")
    result = runner.invoke(app, ["body-fitted", "run", str(config_path)])
    assert result.exit_code == 0, result.output

    # read back
    expected = generate_body_fitted(config_path).grid
    written = read_file(tmp_path / "plate_local.h5", orient=False)

    # check: same (ni, nj, 1) points in double precision, markers restored as a dict
    np.testing.assert_array_equal(written.grid.x, expected.x)
    np.testing.assert_array_equal(written.grid.y, expected.y)
    assert written.attrs["markers"] == {"structured": BOUNDARY_MARKERS}


@pytest.mark.parametrize(
    ("order", "line_type", "quad_type", "n_quads"), [(1, 1, 3, 20000), (2, 8, 10, 5000)]
)
def test_cli_msh_has_the_element_order(
    tmp_path: Path, order: int, line_type: int, quad_type: int, n_quads: int
) -> None:
    """.msh output uses the configured order: 4-node quads per cell, or 9-node quads per 2 x 2 cells."""

    # config writing Gmsh at the given order
    config_path = write_order_2_config(tmp_path, "order = 2", f"order = {order}")
    result = runner.invoke(app, ["body-fitted", "run", str(config_path)])
    assert result.exit_code == 0, result.output

    # element block headers: "dimension entity type count"
    msh_lines = (tmp_path / "plate_local.msh").read_text().splitlines()
    elements_start = msh_lines.index("$Elements")
    n_blocks = int(msh_lines[elements_start + 1].split()[0])
    block_headers = []
    cursor = elements_start + 2
    for _ in range(n_blocks):
        dim, _, element_type, count = (int(v) for v in msh_lines[cursor].split())
        block_headers.append((dim, element_type, count))
        cursor += 1 + count

    # check: four boundary-line blocks, then the quads
    assert [header[1] for header in block_headers[:4]] == [line_type] * 4
    assert block_headers[4] == (2, quad_type, n_quads)


def test_cli_run_reports_errors_cleanly(tmp_path: Path) -> None:
    """A bad config exits with an error message, not a traceback."""

    # config with x_end past the plate
    config_path = write_config(tmp_path, "x_end = 0.01", "x_end = 0.6")
    result = runner.invoke(app, ["body-fitted", "run", str(config_path)])

    # check
    assert result.exit_code == 1
    assert "must not exceed" in result.output
