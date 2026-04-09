"""Tests for items.py — pickup, drop, and usage."""

import pytest

from dice_rangers.board import Board, Coordinate
from dice_rangers.items import (
    can_move_onto_item_square,
    drop_item,
    get_valid_drop_squares,
    pickup_item,
    use_item,
)
from dice_rangers.units import Customization, create_unit

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_unit(unit_id="u1", team=1):
    c = Customization(
        race="race_bird",
        variant="eagle",
        outfit="outfit_warrior",
        primary_color="color_red",
        secondary_color="color_blue",
        attack_flavor="atk_sword",
    )
    return create_unit(unit_id, team, c)


def board_with_unit_at(unit_id, coord):
    board = Board()
    board.unit_positions[unit_id] = coord
    return board


# ---------------------------------------------------------------------------
# pickup_item — no item carried
# ---------------------------------------------------------------------------

def test_pickup_no_item_carried():
    unit = make_unit()
    coord = Coordinate(3, 3)
    board = board_with_unit_at(unit.unit_id, coord)
    board.item_positions[coord] = "item_heal"

    result = pickup_item(board, unit)

    assert result.picked_up == "item_heal"
    assert result.dropped is None
    assert result.needs_drop_location is False
    assert unit.carrying_item == "item_heal"
    assert coord not in board.item_positions
    assert unit.has_acted is True


# ---------------------------------------------------------------------------
# pickup_item — swap (already carrying)
# ---------------------------------------------------------------------------

def test_pickup_swap_item():
    unit = make_unit()
    unit.carrying_item = "item_atk"
    coord = Coordinate(3, 3)
    board = board_with_unit_at(unit.unit_id, coord)
    board.item_positions[coord] = "item_heal"

    result = pickup_item(board, unit)

    assert result.picked_up == "item_heal"
    assert result.dropped == "item_atk"
    assert result.needs_drop_location is True
    assert unit.carrying_item == "item_heal"
    assert coord not in board.item_positions
    assert unit.has_acted is True


# ---------------------------------------------------------------------------
# get_valid_drop_squares
# ---------------------------------------------------------------------------

def test_get_valid_drop_squares_returns_empty_adjacent():
    board = Board()
    coord = Coordinate(3, 3)
    drops = get_valid_drop_squares(board, coord)
    # All 8 adjacent squares should be empty on a fresh board
    assert len(drops) == 8


def test_get_valid_drop_squares_excludes_occupied():
    board = Board()
    coord = Coordinate(3, 3)
    # Block all adjacent squares
    for sq in board.get_adjacent_squares(coord):
        board.obstacles.add(sq)
    drops = get_valid_drop_squares(board, coord)
    assert drops == []


def test_get_valid_drop_squares_excludes_items():
    board = Board()
    coord = Coordinate(3, 3)
    adj = board.get_adjacent_squares(coord)
    # Place an item on one adjacent square
    board.item_positions[adj[0]] = "item_heal"
    drops = get_valid_drop_squares(board, coord)
    assert adj[0] not in drops
    assert len(drops) == len(adj) - 1


# ---------------------------------------------------------------------------
# drop_item
# ---------------------------------------------------------------------------

def test_drop_item_on_empty_square():
    board = Board()
    coord = Coordinate(2, 2)
    drop_item(board, "item_def", coord)
    assert board.item_positions[coord] == "item_def"


def test_drop_item_on_occupied_square_raises():
    board = Board()
    coord = Coordinate(2, 2)
    board.obstacles.add(coord)
    with pytest.raises(ValueError):
        drop_item(board, "item_def", coord)


# ---------------------------------------------------------------------------
# can_move_onto_item_square
# ---------------------------------------------------------------------------

def test_can_move_onto_item_square_not_carrying():
    unit = make_unit()
    board = board_with_unit_at(unit.unit_id, Coordinate(0, 0))
    item_coord = Coordinate(3, 3)
    board.item_positions[item_coord] = "item_heal"
    assert can_move_onto_item_square(board, unit, item_coord) is True


def test_can_move_onto_item_square_carrying_with_drop_space():
    unit = make_unit()
    unit.carrying_item = "item_atk"
    board = board_with_unit_at(unit.unit_id, Coordinate(0, 0))
    item_coord = Coordinate(3, 3)
    board.item_positions[item_coord] = "item_heal"
    # Adjacent squares are empty, so drop is possible
    assert can_move_onto_item_square(board, unit, item_coord) is True


def test_can_move_onto_item_square_carrying_no_drop_space():
    unit = make_unit()
    unit.carrying_item = "item_atk"
    board = board_with_unit_at(unit.unit_id, Coordinate(0, 0))
    item_coord = Coordinate(3, 3)
    board.item_positions[item_coord] = "item_heal"
    # Block all adjacent squares
    for sq in board.get_adjacent_squares(item_coord):
        board.obstacles.add(sq)
    assert can_move_onto_item_square(board, unit, item_coord) is False


def test_can_move_onto_non_item_square_always_true():
    unit = make_unit()
    unit.carrying_item = "item_atk"
    board = board_with_unit_at(unit.unit_id, Coordinate(0, 0))
    empty_coord = Coordinate(5, 5)
    assert can_move_onto_item_square(board, unit, empty_coord) is True


# ---------------------------------------------------------------------------
# use_item
# ---------------------------------------------------------------------------

def test_use_item_heal():
    unit = make_unit()
    unit.carrying_item = "item_heal"
    result = use_item(unit, team_morale=10)
    assert result.item_used == "item_heal"
    assert result.new_morale == 16  # 10 + 6
    assert result.buff_activated is None
    assert unit.carrying_item is None
    assert unit.has_acted is True


def test_use_item_heal_capped_at_max():
    unit = make_unit()
    unit.carrying_item = "item_heal"
    result = use_item(unit, team_morale=18)
    assert result.new_morale == 20  # capped at MAX_MORALE


def test_use_item_atk_boost():
    unit = make_unit()
    unit.carrying_item = "item_atk"
    result = use_item(unit, team_morale=15)
    assert result.item_used == "item_atk"
    assert result.buff_activated == "atk_boost"
    assert unit.atk_boost_active is True
    assert unit.carrying_item is None
    assert result.new_morale == 15  # unchanged


def test_use_item_def_boost():
    unit = make_unit()
    unit.carrying_item = "item_def"
    result = use_item(unit, team_morale=15)
    assert result.item_used == "item_def"
    assert result.buff_activated == "def_boost"
    assert unit.def_boost_active is True
    assert unit.carrying_item is None
    assert result.new_morale == 15  # unchanged


def test_use_item_no_item_raises():
    unit = make_unit()
    with pytest.raises(ValueError):
        use_item(unit, team_morale=15)


def test_use_item_sets_has_acted():
    unit = make_unit()
    unit.carrying_item = "item_heal"
    use_item(unit, team_morale=10)
    assert unit.has_acted is True
