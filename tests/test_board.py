"""Tests for board.py — Grid, Coordinates, Obstacles, Movement, LOS."""

import pytest

from dice_rangers.board import Board, Coordinate

# ---------------------------------------------------------------------------
# Coordinate conversion
# ---------------------------------------------------------------------------

def test_coordinate_from_label_basic():
    coord = Coordinate.from_label("A1")
    assert coord.col == 0
    assert coord.row == 0


def test_coordinate_from_label_last():
    coord = Coordinate.from_label("H8")
    assert coord.col == 7
    assert coord.row == 7


def test_coordinate_from_label_middle():
    coord = Coordinate.from_label("D4")
    assert coord.col == 3
    assert coord.row == 3


def test_coordinate_to_label_basic():
    assert Coordinate(col=0, row=0).to_label() == "A1"


def test_coordinate_to_label_last():
    assert Coordinate(col=7, row=7).to_label() == "H8"


def test_coordinate_to_label_middle():
    assert Coordinate(col=3, row=3).to_label() == "D4"


def test_coordinate_roundtrip():
    for label in ["A1", "H8", "B2", "G7", "D4", "E5"]:
        assert Coordinate.from_label(label).to_label() == label


def test_coordinate_from_label_lowercase():
    coord = Coordinate.from_label("b3")
    assert coord.col == 1
    assert coord.row == 2


def test_coordinate_from_label_invalid_col():
    with pytest.raises(ValueError):
        Coordinate.from_label("Z1")


def test_coordinate_from_label_invalid_row():
    with pytest.raises(ValueError):
        Coordinate.from_label("A9")


def test_coordinate_from_label_invalid_length():
    with pytest.raises(ValueError):
        Coordinate.from_label("A10")


# ---------------------------------------------------------------------------
# is_edge_square
# ---------------------------------------------------------------------------

def test_edge_square_row1():
    board = Board()
    for col in range(8):
        assert board.is_edge_square(Coordinate(col=col, row=0))  # row 1


def test_edge_square_row8():
    board = Board()
    for col in range(8):
        assert board.is_edge_square(Coordinate(col=col, row=7))  # row 8


def test_edge_square_col_a():
    board = Board()
    for row in range(8):
        assert board.is_edge_square(Coordinate(col=0, row=row))  # col A


def test_edge_square_col_h():
    board = Board()
    for row in range(8):
        assert board.is_edge_square(Coordinate(col=7, row=row))  # col H


def test_not_edge_square_interior():
    board = Board()
    # B2 through G7 are interior
    for col in range(1, 7):
        for row in range(1, 7):
            assert not board.is_edge_square(Coordinate(col=col, row=row))


# ---------------------------------------------------------------------------
# Obstacle placement
# ---------------------------------------------------------------------------

def test_place_obstacle_valid():
    board = Board()
    coord = Coordinate.from_label("D4")
    result = board.place_obstacle(coord)
    assert result is True
    assert coord in board.obstacles


def test_place_obstacle_on_edge_raises():
    board = Board()
    with pytest.raises(ValueError):
        board.place_obstacle(Coordinate.from_label("A1"))


def test_place_obstacle_on_edge_row_raises():
    board = Board()
    with pytest.raises(ValueError):
        board.place_obstacle(Coordinate.from_label("D1"))


def test_place_obstacle_on_edge_col_raises():
    board = Board()
    with pytest.raises(ValueError):
        board.place_obstacle(Coordinate.from_label("H4"))


def test_place_obstacle_on_existing_obstacle_raises():
    board = Board()
    coord = Coordinate.from_label("D4")
    board.place_obstacle(coord)
    with pytest.raises(ValueError):
        board.place_obstacle(coord)


def test_place_obstacle_on_unit_raises():
    board = Board()
    coord = Coordinate.from_label("D4")
    board.unit_positions["unit1"] = coord
    with pytest.raises(ValueError):
        board.place_obstacle(coord)


def test_place_obstacle_on_item_raises():
    board = Board()
    coord = Coordinate.from_label("D4")
    board.item_positions[coord] = "sword"
    with pytest.raises(ValueError):
        board.place_obstacle(coord)


# ---------------------------------------------------------------------------
# get_adjacent_squares
# ---------------------------------------------------------------------------

def test_adjacent_corner_a1():
    board = Board()
    coord = Coordinate.from_label("A1")
    adj = board.get_adjacent_squares(coord)
    labels = {c.to_label() for c in adj}
    assert labels == {"A2", "B1", "B2"}


def test_adjacent_corner_h8():
    board = Board()
    coord = Coordinate.from_label("H8")
    adj = board.get_adjacent_squares(coord)
    labels = {c.to_label() for c in adj}
    assert labels == {"G7", "G8", "H7"}


def test_adjacent_edge_d1():
    board = Board()
    coord = Coordinate.from_label("D1")
    adj = board.get_adjacent_squares(coord)
    labels = {c.to_label() for c in adj}
    assert labels == {"C1", "E1", "C2", "D2", "E2"}


def test_adjacent_center_d4():
    board = Board()
    coord = Coordinate.from_label("D4")
    adj = board.get_adjacent_squares(coord)
    labels = {c.to_label() for c in adj}
    assert labels == {"C3", "D3", "E3", "C4", "E4", "C5", "D5", "E5"}


def test_adjacent_count_center():
    board = Board()
    coord = Coordinate(col=3, row=3)
    assert len(board.get_adjacent_squares(coord)) == 8


def test_adjacent_count_corner():
    board = Board()
    coord = Coordinate(col=0, row=0)
    assert len(board.get_adjacent_squares(coord)) == 3


# ---------------------------------------------------------------------------
# get_reachable_squares
# ---------------------------------------------------------------------------

def test_reachable_zero_steps():
    board = Board()
    start = Coordinate.from_label("D4")
    reachable = board.get_reachable_squares(start, 0)
    assert len(reachable) == 0


def test_reachable_one_step_open():
    board = Board()
    start = Coordinate.from_label("D4")
    reachable = board.get_reachable_squares(start, 1)
    labels = {c.to_label() for c in reachable}
    # Orthogonal only: C4, E4, D3, D5
    assert labels == {"C4", "E4", "D3", "D5"}


def test_reachable_no_diagonal():
    """Diagonal squares should NOT be reachable in 1 step."""
    board = Board()
    start = Coordinate.from_label("D4")
    reachable = board.get_reachable_squares(start, 1)
    labels = {c.to_label() for c in reachable}
    # Diagonal neighbors should not be included
    for diag in ["C3", "E3", "C5", "E5"]:
        assert diag not in labels


def test_reachable_does_not_include_start():
    board = Board()
    start = Coordinate.from_label("D4")
    reachable = board.get_reachable_squares(start, 3)
    assert start not in reachable


def test_reachable_blocked_by_obstacle():
    board = Board()
    start = Coordinate.from_label("D4")
    # Place obstacle directly above
    board.obstacles.add(Coordinate.from_label("D5"))
    reachable = board.get_reachable_squares(start, 3)
    # D5 itself should not be reachable
    assert Coordinate.from_label("D5") not in reachable
    # D6 should not be reachable (blocked path through D5)
    assert Coordinate.from_label("D6") not in reachable


def test_reachable_blocked_by_unit():
    board = Board()
    start = Coordinate.from_label("D4")
    board.unit_positions["enemy"] = Coordinate.from_label("D5")
    reachable = board.get_reachable_squares(start, 3)
    assert Coordinate.from_label("D5") not in reachable
    assert Coordinate.from_label("D6") not in reachable


def test_reachable_respects_max_steps():
    board = Board()
    start = Coordinate.from_label("D4")
    reachable = board.get_reachable_squares(start, 2)
    # D6 is 2 steps away (D4->D5->D6)
    assert Coordinate.from_label("D6") in reachable
    # D7 is 3 steps away — should NOT be reachable with max_steps=2
    assert Coordinate.from_label("D7") not in reachable


def test_reachable_items_are_passable():
    """Items on a square do not block movement."""
    board = Board()
    start = Coordinate.from_label("D4")
    board.item_positions[Coordinate.from_label("D5")] = "potion"
    reachable = board.get_reachable_squares(start, 2)
    # D5 has an item but is passable
    assert Coordinate.from_label("D5") in reachable
    # D6 is reachable through D5
    assert Coordinate.from_label("D6") in reachable


# ---------------------------------------------------------------------------
# has_line_of_sight
# ---------------------------------------------------------------------------

def test_los_horizontal_clear():
    board = Board()
    origin = Coordinate.from_label("B4")
    target = Coordinate.from_label("D4")
    assert board.has_line_of_sight(origin, target) is True


def test_los_vertical_clear():
    board = Board()
    origin = Coordinate.from_label("D2")
    target = Coordinate.from_label("D4")
    assert board.has_line_of_sight(origin, target) is True


def test_los_diagonal_clear():
    board = Board()
    origin = Coordinate.from_label("B2")
    target = Coordinate.from_label("D4")
    assert board.has_line_of_sight(origin, target) is True


def test_los_blocked_by_obstacle():
    board = Board()
    origin = Coordinate.from_label("B4")
    target = Coordinate.from_label("D4")
    board.obstacles.add(Coordinate.from_label("C4"))
    assert board.has_line_of_sight(origin, target) is False


def test_los_blocked_by_unit():
    board = Board()
    origin = Coordinate.from_label("B4")
    target = Coordinate.from_label("D4")
    board.unit_positions["blocker"] = Coordinate.from_label("C4")
    assert board.has_line_of_sight(origin, target) is False


def test_los_target_can_have_unit():
    """Target square may contain a unit (the attack target)."""
    board = Board()
    origin = Coordinate.from_label("B4")
    target = Coordinate.from_label("D4")
    board.unit_positions["enemy"] = target
    assert board.has_line_of_sight(origin, target) is True


def test_los_non_straight_line_fails():
    board = Board()
    origin = Coordinate.from_label("B2")
    target = Coordinate.from_label("D3")  # dx=2, dy=1 — not straight
    assert board.has_line_of_sight(origin, target) is False


def test_los_beyond_range_fails():
    board = Board()
    origin = Coordinate.from_label("A4")
    target = Coordinate.from_label("E4")  # distance 4 > MAX_RANGED_DISTANCE=3
    assert board.has_line_of_sight(origin, target) is False


def test_los_exactly_range_3():
    board = Board()
    origin = Coordinate.from_label("B4")
    target = Coordinate.from_label("E4")  # distance exactly 3
    assert board.has_line_of_sight(origin, target) is True


def test_los_same_square_fails():
    """Origin and target are the same — distance 0, should fail."""
    board = Board()
    coord = Coordinate.from_label("D4")
    assert board.has_line_of_sight(coord, coord) is False


def test_los_diagonal_blocked():
    board = Board()
    origin = Coordinate.from_label("B2")
    target = Coordinate.from_label("D4")
    board.obstacles.add(Coordinate.from_label("C3"))
    assert board.has_line_of_sight(origin, target) is False
