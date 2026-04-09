"""Pure math tests for renderer coordinate helpers.

These tests do NOT require a display or pygame initialization — they only
exercise grid_to_pixel and pixel_to_grid which are pure arithmetic functions.
"""

from __future__ import annotations

import os

import pytest

# Prevent pygame from trying to open a display during import
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Skip entire module if pygame is not installed (headless/CI environments)
pygame = pytest.importorskip("pygame")

from dice_rangers.board import Coordinate  # noqa: E402
from dice_rangers.constants import (  # noqa: E402
    GRID_ORIGIN_X,
    GRID_ORIGIN_Y,
    GRID_SIZE,
    TILE_SIZE,
    WINDOW_SIZE,
)
from dice_rangers.renderer import grid_to_pixel, pixel_to_grid  # noqa: E402

# ---------------------------------------------------------------------------
# grid_to_pixel tests
# ---------------------------------------------------------------------------


def test_grid_to_pixel_origin():
    """Coordinate(0, 0) maps to the grid origin pixel."""
    assert grid_to_pixel(Coordinate(0, 0)) == (GRID_ORIGIN_X, GRID_ORIGIN_Y)


def test_grid_to_pixel_max():
    """Coordinate(7, 7) maps to the correct bottom-right tile pixel."""
    assert grid_to_pixel(Coordinate(7, 7)) == (
        GRID_ORIGIN_X + 7 * TILE_SIZE,
        GRID_ORIGIN_Y + 7 * TILE_SIZE,
    )


def test_grid_to_pixel_mid():
    """Coordinate(3, 4) maps correctly."""
    assert grid_to_pixel(Coordinate(3, 4)) == (
        GRID_ORIGIN_X + 3 * TILE_SIZE,
        GRID_ORIGIN_Y + 4 * TILE_SIZE,
    )


# ---------------------------------------------------------------------------
# pixel_to_grid tests
# ---------------------------------------------------------------------------


def test_pixel_to_grid_tile_a1_center():
    """Center of tile A1 maps to Coordinate(0, 0)."""
    px = GRID_ORIGIN_X + 48
    py = GRID_ORIGIN_Y + 48
    assert pixel_to_grid(px, py) == Coordinate(0, 0)


def test_pixel_to_grid_tile_h8_center():
    """Center of tile H8 maps to Coordinate(7, 7)."""
    px = GRID_ORIGIN_X + TILE_SIZE * 7 + 48
    py = GRID_ORIGIN_Y + TILE_SIZE * 7 + 48
    assert pixel_to_grid(px, py) == Coordinate(7, 7)


def test_pixel_to_grid_outside_top_left():
    """Pixel (0, 0) is in the margin — returns None."""
    assert pixel_to_grid(0, 0) is None


def test_pixel_to_grid_outside_bottom_right():
    """Pixel at WINDOW_SIZE is one beyond the surface — returns None."""
    assert pixel_to_grid(WINDOW_SIZE, WINDOW_SIZE) is None


def test_pixel_to_grid_just_inside_grid():
    """Top-left corner of tile A1 is inside the grid."""
    assert pixel_to_grid(GRID_ORIGIN_X, GRID_ORIGIN_Y) == Coordinate(0, 0)


def test_pixel_to_grid_just_outside_right():
    """One pixel past the right edge of the grid returns None."""
    px = GRID_ORIGIN_X + GRID_SIZE * TILE_SIZE
    py = GRID_ORIGIN_Y
    assert pixel_to_grid(px, py) is None


def test_pixel_to_grid_just_outside_bottom():
    """One pixel past the bottom edge of the grid returns None."""
    px = GRID_ORIGIN_X
    py = GRID_ORIGIN_Y + GRID_SIZE * TILE_SIZE
    assert pixel_to_grid(px, py) is None


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "coord",
    [Coordinate(col, row) for col in range(GRID_SIZE) for row in range(GRID_SIZE)],
)
def test_round_trip(coord: Coordinate):
    """pixel_to_grid(grid_to_pixel(coord)) == coord for all valid coordinates."""
    px, py = grid_to_pixel(coord)
    assert pixel_to_grid(px, py) == coord
