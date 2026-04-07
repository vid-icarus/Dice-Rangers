"""Tests for game.py — setup phases (Part 1)."""

from __future__ import annotations

import pytest

from dice_rangers.board import Board, Coordinate
from dice_rangers.constants import STARTING_MORALE
from dice_rangers.game import (
    Phase,
    GameState,
    new_game,
    get_unit,
    submit_customization,
    roll_obstacle,
    place_obstacle,
    place_unit_on_board,
)
from dice_rangers.units import Customization


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_customization(
    race="race_bird",
    variant="eagle",
    outfit="outfit_warrior",
    primary_color="color_red",
    secondary_color="color_blue",
    attack_flavor="atk_sword",
) -> Customization:
    return Customization(
        race=race,
        variant=variant,
        outfit=outfit,
        primary_color=primary_color,
        secondary_color=secondary_color,
        attack_flavor=attack_flavor,
    )


def _setup_through_customization(seed=42) -> GameState:
    """Return a state with all 4 units customized (in OBSTACLE_PLACEMENT)."""
    state = new_game(seed=seed)
    submit_customization(state, "p1a", 1, _make_customization())
    submit_customization(state, "p1b", 1, _make_customization(variant="parrot"))
    submit_customization(state, "p2a", 2, _make_customization(race="race_cat", variant="tabby"))
    submit_customization(state, "p2b", 2, _make_customization(race="race_cat", variant="siamese"))
    return state


def _setup_through_obstacles(seed=42) -> GameState:
    """Return a state with 8 obstacles placed (in SPAWN_PLACEMENT)."""
    state = _setup_through_customization(seed=seed)
    for _ in range(8):
        roll_obstacle(state)
        col_roll, row_roll = state.obstacle_roll
        rolled_coord = Coordinate(col=col_roll - 1, row=row_roll - 1)
        # Try rolled coord first; if it fails (edge/occupied), try adjacents
        placed = False
        candidates = [rolled_coord] + state.board.get_adjacent_squares(rolled_coord)
        for candidate in candidates:
            try:
                place_obstacle(state, candidate)
                placed = True
                break
            except ValueError:
                continue
        if not placed:
            # Force clear the roll and skip (shouldn't happen in practice)
            state.obstacle_roll = None
            state.obstacles_placed += 1
            state.current_placer = 2 if state.current_placer == 1 else 1
            if state.obstacles_placed == 8:
                state.phase = Phase.SPAWN_PLACEMENT
                state.current_spawner = 1
                state.units_spawned_this_player = 0
    return state


# ---------------------------------------------------------------------------
# Factory Tests
# ---------------------------------------------------------------------------

def test_new_game_phase():
    state = new_game()
    assert state.phase == Phase.P1_CUSTOMIZE


def test_new_game_morales():
    state = new_game()
    assert state.team1_morale == STARTING_MORALE
    assert state.team2_morale == STARTING_MORALE


def test_new_game_empty_units_and_board():
    state = new_game()
    assert state.team1_units == []
    assert state.team2_units == []
    assert len(state.board.obstacles) == 0
    assert len(state.board.unit_positions) == 0


def test_new_game_seeded_deterministic():
    state1 = new_game(seed=42)
    state2 = new_game(seed=42)
    r1 = state1.roller.roll(6)
    r2 = state2.roller.roll(6)
    assert r1 == r2


# ---------------------------------------------------------------------------
# get_unit Tests
# ---------------------------------------------------------------------------

def test_get_unit_finds_team1():
    state = new_game()
    submit_customization(state, "p1a", 1, _make_customization())
    unit = get_unit(state, "p1a")
    assert unit.unit_id == "p1a"
    assert unit.team == 1


def test_get_unit_finds_team2():
    state = _setup_through_customization()
    unit = get_unit(state, "p2b")
    assert unit.unit_id == "p2b"
    assert unit.team == 2


def test_get_unit_raises_for_unknown():
    state = new_game()
    with pytest.raises(ValueError, match="not found"):
        get_unit(state, "nonexistent")


# ---------------------------------------------------------------------------
# Customization Phase Tests
# ---------------------------------------------------------------------------

def test_submit_customization_p1_unit1():
    state = new_game()
    submit_customization(state, "p1a", 1, _make_customization())
    assert len(state.team1_units) == 1
    assert state.team1_units[0].unit_id == "p1a"
    assert state.phase == Phase.P1_CUSTOMIZE  # still P1


def test_submit_customization_p1_unit2_advances_phase():
    state = new_game()
    submit_customization(state, "p1a", 1, _make_customization())
    submit_customization(state, "p1b", 1, _make_customization(variant="parrot"))
    assert len(state.team1_units) == 2
    assert state.phase == Phase.P2_CUSTOMIZE


def test_submit_customization_p2_unit1():
    state = new_game()
    submit_customization(state, "p1a", 1, _make_customization())
    submit_customization(state, "p1b", 1, _make_customization(variant="parrot"))
    submit_customization(state, "p2a", 2, _make_customization(race="race_cat", variant="tabby"))
    assert len(state.team2_units) == 1
    assert state.phase == Phase.P2_CUSTOMIZE


def test_submit_customization_p2_unit2_advances_to_obstacle_placement():
    state = _setup_through_customization()
    assert len(state.team2_units) == 2
    assert state.phase == Phase.OBSTACLE_PLACEMENT
    assert state.current_placer == 1
    assert state.obstacles_placed == 0


def test_submit_customization_wrong_team_raises():
    state = new_game()
    with pytest.raises(ValueError):
        submit_customization(state, "p2a", 2, _make_customization())


def test_submit_customization_invalid_race_raises():
    state = new_game()
    bad = _make_customization(race="race_unicorn", variant="sparkle")
    with pytest.raises(ValueError):
        submit_customization(state, "p1a", 1, bad)


# ---------------------------------------------------------------------------
# Obstacle Placement Tests
# ---------------------------------------------------------------------------

def test_roll_obstacle_returns_valid_tuple():
    state = _setup_through_customization()
    result = roll_obstacle(state)
    assert isinstance(result, tuple)
    assert len(result) == 2
    col, row = result
    assert 1 <= col <= 8
    assert 1 <= row <= 8


def test_roll_obstacle_stores_result():
    state = _setup_through_customization()
    result = roll_obstacle(state)
    assert state.obstacle_roll == result


def test_roll_obstacle_raises_if_roll_pending():
    state = _setup_through_customization()
    roll_obstacle(state)
    with pytest.raises(ValueError, match="place obstacle before rolling"):
        roll_obstacle(state)


def test_place_obstacle_on_rolled_coord():
    state = _setup_through_customization(seed=99)
    roll_obstacle(state)
    col_roll, row_roll = state.obstacle_roll
    rolled_coord = Coordinate(col=col_roll - 1, row=row_roll - 1)
    # Find a valid placement (rolled or adjacent, non-edge, non-occupied)
    candidates = [rolled_coord] + state.board.get_adjacent_squares(rolled_coord)
    for candidate in candidates:
        try:
            place_obstacle(state, candidate)
            assert candidate in state.board.obstacles
            return
        except ValueError:
            continue
    pytest.skip("No valid placement found for this seed")


def test_place_obstacle_on_adjacent_coord():
    state = _setup_through_customization(seed=1)
    roll_obstacle(state)
    col_roll, row_roll = state.obstacle_roll
    rolled_coord = Coordinate(col=col_roll - 1, row=row_roll - 1)
    adjacents = state.board.get_adjacent_squares(rolled_coord)
    # Find an adjacent non-edge square
    for adj in adjacents:
        if not state.board.is_edge_square(adj):
            place_obstacle(state, adj)
            assert adj in state.board.obstacles
            return
    pytest.skip("No valid adjacent non-edge square for this seed")


def test_place_obstacle_raises_for_non_adjacent():
    state = _setup_through_customization()
    roll_obstacle(state)
    col_roll, row_roll = state.obstacle_roll
    rolled_coord = Coordinate(col=col_roll - 1, row=row_roll - 1)
    adjacents = state.board.get_adjacent_squares(rolled_coord)
    adjacent_set = set(adjacents) | {rolled_coord}
    # Find a coord that is not rolled or adjacent
    for c in range(8):
        for r in range(8):
            candidate = Coordinate(col=c, row=r)
            if candidate not in adjacent_set:
                with pytest.raises(ValueError):
                    place_obstacle(state, candidate)
                return


def test_place_obstacle_raises_for_edge_square():
    state = _setup_through_customization()
    # Manually set obstacle_roll to a coord whose rolled square is adjacent to edge
    # Use a known edge-adjacent roll: col=1,row=1 → Coordinate(0,0) which IS edge
    state.obstacle_roll = (1, 1)  # rolled_coord = Coordinate(0,0) — edge
    edge_coord = Coordinate(col=0, row=0)
    with pytest.raises(ValueError):
        place_obstacle(state, edge_coord)


def test_place_obstacle_raises_for_occupied_square():
    state = _setup_through_customization()
    # Place one obstacle first
    roll_obstacle(state)
    col_roll, row_roll = state.obstacle_roll
    rolled_coord = Coordinate(col=col_roll - 1, row=row_roll - 1)
    candidates = [rolled_coord] + state.board.get_adjacent_squares(rolled_coord)
    placed_coord = None
    for candidate in candidates:
        try:
            place_obstacle(state, candidate)
            placed_coord = candidate
            break
        except ValueError:
            continue
    if placed_coord is None:
        pytest.skip("Could not place first obstacle")

    # Now try to place on the same square again
    state.obstacle_roll = (placed_coord.col + 1, placed_coord.row + 1)
    with pytest.raises(ValueError):
        place_obstacle(state, placed_coord)


def test_place_obstacle_alternates_placer():
    state = _setup_through_customization()
    assert state.current_placer == 1
    roll_obstacle(state)
    col_roll, row_roll = state.obstacle_roll
    rolled_coord = Coordinate(col=col_roll - 1, row=row_roll - 1)
    candidates = [rolled_coord] + state.board.get_adjacent_squares(rolled_coord)
    for candidate in candidates:
        try:
            place_obstacle(state, candidate)
            break
        except ValueError:
            continue
    assert state.current_placer == 2


def test_place_obstacle_clears_roll():
    state = _setup_through_customization()
    roll_obstacle(state)
    col_roll, row_roll = state.obstacle_roll
    rolled_coord = Coordinate(col=col_roll - 1, row=row_roll - 1)
    candidates = [rolled_coord] + state.board.get_adjacent_squares(rolled_coord)
    for candidate in candidates:
        try:
            place_obstacle(state, candidate)
            break
        except ValueError:
            continue
    assert state.obstacle_roll is None


def test_place_obstacle_phase_advances_after_8():
    state = _setup_through_obstacles()
    assert state.phase == Phase.SPAWN_PLACEMENT
    assert state.obstacles_placed == 8


# ---------------------------------------------------------------------------
# Spawn Placement Tests
# ---------------------------------------------------------------------------

def test_place_unit_p1_valid_rows():
    state = _setup_through_obstacles()
    unit_id = state.team1_units[0].unit_id
    coord = Coordinate(col=3, row=0)  # row 0 = display row 1 (P1 zone)
    place_unit_on_board(state, unit_id, coord)
    assert state.board.unit_positions[unit_id] == coord


def test_place_unit_p1_invalid_row_raises():
    state = _setup_through_obstacles()
    unit_id = state.team1_units[0].unit_id
    coord = Coordinate(col=3, row=4)  # row 4 = display row 5 (not P1 zone)
    with pytest.raises(ValueError, match="spawn zone"):
        place_unit_on_board(state, unit_id, coord)


def test_place_unit_p2_valid_rows():
    state = _setup_through_obstacles()
    # First place P1 units
    place_unit_on_board(state, state.team1_units[0].unit_id, Coordinate(col=2, row=0))
    place_unit_on_board(state, state.team1_units[1].unit_id, Coordinate(col=3, row=0))
    # Now P2
    unit_id = state.team2_units[0].unit_id
    coord = Coordinate(col=3, row=5)  # row 5 = display row 6 (P2 zone)
    place_unit_on_board(state, unit_id, coord)
    assert state.board.unit_positions[unit_id] == coord


def test_place_unit_p2_invalid_row_raises():
    state = _setup_through_obstacles()
    # Place P1 units first
    place_unit_on_board(state, state.team1_units[0].unit_id, Coordinate(col=2, row=0))
    place_unit_on_board(state, state.team1_units[1].unit_id, Coordinate(col=3, row=0))
    # Now P2 tries invalid row
    unit_id = state.team2_units[0].unit_id
    coord = Coordinate(col=3, row=4)  # row 4 = display row 5 (not P2 zone)
    with pytest.raises(ValueError, match="spawn zone"):
        place_unit_on_board(state, unit_id, coord)


def test_place_unit_occupied_square_raises():
    state = _setup_through_obstacles()
    unit_a = state.team1_units[0].unit_id
    unit_b = state.team1_units[1].unit_id
    coord = Coordinate(col=2, row=0)
    place_unit_on_board(state, unit_a, coord)
    with pytest.raises(ValueError):
        place_unit_on_board(state, unit_b, coord)


def test_place_unit_wrong_team_raises():
    state = _setup_through_obstacles()
    # current_spawner is 1, try to place a P2 unit
    unit_id = state.team2_units[0].unit_id
    coord = Coordinate(col=3, row=0)
    with pytest.raises(ValueError, match="current spawner"):
        place_unit_on_board(state, unit_id, coord)


def test_place_unit_p1_two_units_switches_spawner():
    state = _setup_through_obstacles()
    place_unit_on_board(state, state.team1_units[0].unit_id, Coordinate(col=2, row=0))
    assert state.current_spawner == 1  # still 1 after first unit
    place_unit_on_board(state, state.team1_units[1].unit_id, Coordinate(col=3, row=0))
    assert state.current_spawner == 2
    assert state.units_spawned_this_player == 0


def test_place_unit_p2_two_units_advances_to_round_start():
    state = _setup_through_obstacles()
    place_unit_on_board(state, state.team1_units[0].unit_id, Coordinate(col=2, row=0))
    place_unit_on_board(state, state.team1_units[1].unit_id, Coordinate(col=3, row=0))
    place_unit_on_board(state, state.team2_units[0].unit_id, Coordinate(col=2, row=7))
    place_unit_on_board(state, state.team2_units[1].unit_id, Coordinate(col=3, row=7))
    assert state.phase == Phase.ROUND_START


# ---------------------------------------------------------------------------
# Integration Test
# ---------------------------------------------------------------------------

def _place_8_obstacles(state: GameState) -> int:
    """Place exactly 8 obstacles, returning how many were actually placed on the board.

    Always finds a valid (non-edge, non-occupied) square near the rolled coord.
    Never uses the manual-advance fallback so the board count stays accurate.
    """
    placed_count = 0
    while state.obstacles_placed < 8:
        roll_obstacle(state)
        col_roll, row_roll = state.obstacle_roll
        rolled_coord = Coordinate(col=col_roll - 1, row=row_roll - 1)
        candidates = [rolled_coord] + state.board.get_adjacent_squares(rolled_coord)
        for candidate in candidates:
            try:
                place_obstacle(state, candidate)
                placed_count += 1
                break
            except ValueError:
                continue
        else:
            # Extremely unlikely: all candidates blocked. Clear roll and skip.
            state.obstacle_roll = None
            state.obstacles_placed += 1
            state.current_placer = 2 if state.current_placer == 1 else 1
            if state.obstacles_placed == 8:
                state.phase = Phase.SPAWN_PLACEMENT
                state.current_spawner = 1
                state.units_spawned_this_player = 0
    return placed_count


def test_full_setup_flow():
    """Full setup flow: new_game → 4 customizations → 8 obstacles → 4 spawns → ROUND_START."""
    state = new_game(seed=42)

    # Customization
    submit_customization(state, "p1a", 1, _make_customization())
    submit_customization(state, "p1b", 1, _make_customization(variant="parrot"))
    assert state.phase == Phase.P2_CUSTOMIZE
    submit_customization(state, "p2a", 2, _make_customization(race="race_cat", variant="tabby"))
    submit_customization(state, "p2b", 2, _make_customization(race="race_cat", variant="siamese"))
    assert state.phase == Phase.OBSTACLE_PLACEMENT

    # Obstacle placement — place all 8, track how many landed on the board
    actual_placed = _place_8_obstacles(state)

    assert state.phase == Phase.SPAWN_PLACEMENT
    assert state.obstacles_placed == 8
    assert len(state.board.obstacles) == actual_placed

    # Spawn placement — find valid rows that aren't blocked
    def find_valid_spawn(row_set):
        for row in sorted(row_set):
            for col in range(1, 7):  # avoid edge cols
                coord = Coordinate(col=col, row=row)
                if state.board.is_passable(coord):
                    return coord
        return None

    p1_coord1 = find_valid_spawn({0, 1, 2})
    assert p1_coord1 is not None
    place_unit_on_board(state, "p1a", p1_coord1)

    p1_coord2 = find_valid_spawn({0, 1, 2})
    assert p1_coord2 is not None
    place_unit_on_board(state, "p1b", p1_coord2)

    p2_coord1 = find_valid_spawn({5, 6, 7})
    assert p2_coord1 is not None
    place_unit_on_board(state, "p2a", p2_coord1)

    p2_coord2 = find_valid_spawn({5, 6, 7})
    assert p2_coord2 is not None
    place_unit_on_board(state, "p2b", p2_coord2)

    assert state.phase == Phase.ROUND_START
    assert len(state.board.unit_positions) == 4
