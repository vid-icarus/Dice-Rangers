"""Tests for game.py — setup phases (Part 1) and game loop (Part 2)."""

from __future__ import annotations

import pytest

from dice_rangers.board import Coordinate
from dice_rangers.constants import STARTING_MORALE
from dice_rangers.game import (
    GameState,
    Phase,
    begin_activation,
    do_attack,
    do_drop_item,
    do_move,
    do_skip_action,
    do_use_item,
    end_activation,
    get_attackable_targets,
    get_choosable_units,
    get_current_team,
    get_drop_squares,
    get_reachable_squares,
    get_team_morale,
    get_unit,
    get_valid_actions,
    new_game,
    place_obstacle,
    place_unit_on_board,
    resolve_round_start,
    roll_obstacle,
    submit_customization,
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


def _setup_through_round_start(seed=42) -> GameState:
    """Return a state fully set up and in ROUND_START phase."""
    state = _setup_through_obstacles(seed=seed)
    # Place P1 units in rows 1-2 (0-indexed: rows 0-1)
    place_unit_on_board(state, state.team1_units[0].unit_id, Coordinate(col=2, row=0))
    place_unit_on_board(state, state.team1_units[1].unit_id, Coordinate(col=3, row=0))
    # Place P2 units in rows 6-7 (0-indexed)
    place_unit_on_board(state, state.team2_units[0].unit_id, Coordinate(col=2, row=7))
    place_unit_on_board(state, state.team2_units[1].unit_id, Coordinate(col=3, row=7))
    assert state.phase == Phase.ROUND_START
    return state


def _setup_through_activation(seed=42) -> GameState:
    """Return a state in ACTIVATION phase (round start resolved)."""
    state = _setup_through_round_start(seed=seed)
    resolve_round_start(state)
    assert state.phase == Phase.ACTIVATION
    return state


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


# ---------------------------------------------------------------------------
# Part 2: resolve_round_start Tests
# ---------------------------------------------------------------------------

def test_resolve_round_start_returns_board_event():
    from dice_rangers.events import BoardEvent
    state = _setup_through_round_start()
    event = resolve_round_start(state)
    assert isinstance(event, BoardEvent)


def test_resolve_round_start_stores_current_event():
    state = _setup_through_round_start()
    event = resolve_round_start(state)
    assert state.current_event is event


def test_resolve_round_start_resets_activation_index():
    state = _setup_through_round_start()
    state.activation_index = 3  # simulate mid-round
    resolve_round_start(state)
    assert state.activation_index == 0


def test_resolve_round_start_advances_to_activation():
    state = _setup_through_round_start()
    resolve_round_start(state)
    assert state.phase == Phase.ACTIVATION


def test_resolve_round_start_raises_wrong_phase():
    state = _setup_through_activation()
    with pytest.raises(ValueError):
        resolve_round_start(state)


# ---------------------------------------------------------------------------
# Part 2: begin_activation Tests
# ---------------------------------------------------------------------------

def test_begin_activation_returns_movement_roll():
    state = _setup_through_activation()
    roll = begin_activation(state, state.team1_units[0].unit_id)
    assert 1 <= roll <= 6


def test_begin_activation_stores_movement_roll():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    roll = begin_activation(state, uid)
    assert state.movement_roll == roll


def test_begin_activation_sets_active_unit_id():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    begin_activation(state, uid)
    assert state.active_unit_id == uid


def test_begin_activation_resets_has_moved_and_has_acted():
    state = _setup_through_activation()
    unit = state.team1_units[0]
    unit.has_moved = True
    unit.has_acted = True
    begin_activation(state, unit.unit_id)
    assert unit.has_moved is False
    assert unit.has_acted is False


def test_begin_activation_raises_wrong_team():
    state = _setup_through_activation()
    # activation_index=0 → team 1's turn; P2 unit should fail
    p2_uid = state.team2_units[0].unit_id
    with pytest.raises(ValueError):
        begin_activation(state, p2_uid)


def test_begin_activation_raises_same_unit_as_last_activated():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    # Simulate that this unit was last activated for team 1
    state.last_activated[1] = uid
    with pytest.raises(ValueError):
        begin_activation(state, uid)


def test_begin_activation_allows_either_unit_on_first_activation():
    state = _setup_through_activation()
    # last_activated[1] is None → either P1 unit is valid
    uid = state.team1_units[1].unit_id
    roll = begin_activation(state, uid)
    assert 1 <= roll <= 6
    assert state.active_unit_id == uid


def test_begin_activation_raises_if_previous_not_ended():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    begin_activation(state, uid)
    with pytest.raises(ValueError):
        begin_activation(state, uid)


def test_begin_activation_raises_unit_not_on_board():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    # Remove unit from board
    del state.board.unit_positions[uid]
    with pytest.raises(ValueError):
        begin_activation(state, uid)


# ---------------------------------------------------------------------------
# Part 2: do_move Tests
# ---------------------------------------------------------------------------

def test_do_move_moves_unit():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    begin_activation(state, uid)
    src = state.board.unit_positions[uid]
    # Move one step down (row+1)
    dest = Coordinate(col=src.col, row=src.row + 1)
    do_move(state, dest)
    assert state.board.unit_positions[uid] == dest


def test_do_move_sets_has_moved():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    begin_activation(state, uid)
    src = state.board.unit_positions[uid]
    dest = Coordinate(col=src.col, row=src.row + 1)
    do_move(state, dest)
    assert get_unit(state, uid).has_moved is True


def test_do_move_raises_if_already_moved():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    begin_activation(state, uid)
    src = state.board.unit_positions[uid]
    dest = Coordinate(col=src.col, row=src.row + 1)
    do_move(state, dest)
    with pytest.raises(ValueError):
        do_move(state, Coordinate(col=src.col, row=src.row + 2))


def test_do_move_raises_unreachable_destination():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    # Force movement_roll to 1 so far squares are unreachable
    begin_activation(state, uid)
    state.movement_roll = 1
    src = state.board.unit_positions[uid]
    # Try to move 5 squares away
    far_dest = Coordinate(col=src.col, row=min(7, src.row + 5))
    with pytest.raises(ValueError):
        do_move(state, far_dest)


def test_do_move_returns_none_when_no_item():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    begin_activation(state, uid)
    src = state.board.unit_positions[uid]
    dest = Coordinate(col=src.col, row=src.row + 1)
    result = do_move(state, dest)
    assert result is None


def test_do_move_auto_pickup_item():
    from dice_rangers.items import PickupResult
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    src = state.board.unit_positions[uid]
    # Place an item adjacent to the unit
    item_dest = Coordinate(col=src.col, row=src.row + 1)
    state.board.item_positions[item_dest] = "item_heal"
    begin_activation(state, uid)
    state.movement_roll = 6  # ensure reachable
    result = do_move(state, item_dest)
    assert isinstance(result, PickupResult)
    assert result.picked_up == "item_heal"


def test_do_move_raises_wrong_phase():
    state = _setup_through_round_start()
    with pytest.raises(ValueError):
        do_move(state, Coordinate(col=0, row=0))


def test_do_move_raises_no_active_unit():
    state = _setup_through_activation()
    with pytest.raises(ValueError):
        do_move(state, Coordinate(col=0, row=0))


# ---------------------------------------------------------------------------
# Part 2: do_attack Tests
# ---------------------------------------------------------------------------

def _setup_adjacent_combat(seed=42):
    """Set up state with P1 unit adjacent to P2 unit, P1 activated."""
    state = _setup_through_activation(seed=seed)
    p1_uid = state.team1_units[0].unit_id
    p2_uid = state.team2_units[0].unit_id
    # Place units adjacent to each other
    state.board.unit_positions[p1_uid] = Coordinate(col=4, row=3)
    state.board.unit_positions[p2_uid] = Coordinate(col=4, row=4)
    begin_activation(state, p1_uid)
    return state, p1_uid, p2_uid


def test_do_attack_returns_attack_result():
    from dice_rangers.units import AttackResult
    state, p1_uid, p2_uid = _setup_adjacent_combat()
    result = do_attack(state, p2_uid)
    assert isinstance(result, AttackResult)


def test_do_attack_applies_damage_to_defender_morale():
    state, p1_uid, p2_uid = _setup_adjacent_combat(seed=1)
    initial_morale = state.team2_morale
    result = do_attack(state, p2_uid)
    assert state.team2_morale == max(0, initial_morale - result.net_damage)


def test_do_attack_raises_if_already_acted():
    state, p1_uid, p2_uid = _setup_adjacent_combat()
    do_attack(state, p2_uid)
    with pytest.raises(ValueError):
        do_attack(state, p2_uid)


def test_do_attack_raises_same_team():
    state = _setup_through_activation()
    p1_uid = state.team1_units[0].unit_id
    p1_uid2 = state.team1_units[1].unit_id
    state.board.unit_positions[p1_uid] = Coordinate(col=4, row=3)
    state.board.unit_positions[p1_uid2] = Coordinate(col=4, row=4)
    begin_activation(state, p1_uid)
    with pytest.raises(ValueError):
        do_attack(state, p1_uid2)


def test_do_attack_victory_when_morale_reaches_zero():
    state, p1_uid, p2_uid = _setup_adjacent_combat()
    state.team2_morale = 1  # one hit should finish them
    do_attack(state, p2_uid)
    if state.team2_morale <= 0:
        assert state.phase == Phase.VICTORY
        assert state.winner == 1


def test_do_attack_raises_wrong_phase():
    state = _setup_through_round_start()
    with pytest.raises(ValueError):
        do_attack(state, "p2a")


def test_do_attack_raises_no_active_unit():
    state = _setup_through_activation()
    with pytest.raises(ValueError):
        do_attack(state, "p2a")


# ---------------------------------------------------------------------------
# Part 2: do_use_item Tests
# ---------------------------------------------------------------------------

def _setup_unit_with_item(item_id="item_heal", seed=42):
    """Set up state with P1 unit carrying an item, activated."""
    state = _setup_through_activation(seed=seed)
    uid = state.team1_units[0].unit_id
    unit = get_unit(state, uid)
    unit.carrying_item = item_id
    begin_activation(state, uid)
    return state, uid


def test_do_use_item_heal_increases_morale():
    state, uid = _setup_unit_with_item("item_heal")
    state.team1_morale = 10
    result = do_use_item(state)
    assert state.team1_morale > 10


def test_do_use_item_atk_boost_sets_flag():
    state, uid = _setup_unit_with_item("item_atk")
    do_use_item(state)
    unit = get_unit(state, uid)
    assert unit.atk_boost_active is True


def test_do_use_item_def_boost_sets_flag():
    state, uid = _setup_unit_with_item("item_def")
    do_use_item(state)
    unit = get_unit(state, uid)
    assert unit.def_boost_active is True


def test_do_use_item_raises_if_already_acted():
    state, uid = _setup_unit_with_item()
    do_use_item(state)
    with pytest.raises(ValueError):
        do_use_item(state)


def test_do_use_item_raises_if_no_item():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    begin_activation(state, uid)
    with pytest.raises(ValueError):
        do_use_item(state)


def test_do_use_item_raises_wrong_phase():
    state = _setup_through_round_start()
    with pytest.raises(ValueError):
        do_use_item(state)


# ---------------------------------------------------------------------------
# Part 2: do_skip_action Tests
# ---------------------------------------------------------------------------

def test_do_skip_action_sets_has_acted():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    begin_activation(state, uid)
    do_skip_action(state)
    assert get_unit(state, uid).has_acted is True


def test_do_skip_action_raises_if_already_acted():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    begin_activation(state, uid)
    do_skip_action(state)
    with pytest.raises(ValueError):
        do_skip_action(state)


def test_do_skip_action_raises_wrong_phase():
    state = _setup_through_round_start()
    with pytest.raises(ValueError):
        do_skip_action(state)


def test_do_skip_action_raises_no_active_unit():
    state = _setup_through_activation()
    with pytest.raises(ValueError):
        do_skip_action(state)


# ---------------------------------------------------------------------------
# Part 2: end_activation Tests
# ---------------------------------------------------------------------------

def test_end_activation_updates_last_activated():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    begin_activation(state, uid)
    end_activation(state)
    assert state.last_activated[1] == uid


def test_end_activation_increments_activation_index():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    begin_activation(state, uid)
    end_activation(state)
    assert state.activation_index == 1


def test_end_activation_clears_active_unit_and_roll():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    begin_activation(state, uid)
    end_activation(state)
    assert state.active_unit_id is None
    assert state.movement_roll is None


def test_end_activation_stays_in_activation_if_activations_remain():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    begin_activation(state, uid)
    end_activation(state)
    assert state.phase == Phase.ACTIVATION


def test_end_activation_advances_to_round_start_after_4():
    state = _setup_through_activation()
    p1a = state.team1_units[0].unit_id
    p1b = state.team1_units[1].unit_id
    p2a = state.team2_units[0].unit_id
    p2b = state.team2_units[1].unit_id

    # activation_index 0: P1 turn
    begin_activation(state, p1a)
    end_activation(state)
    # activation_index 1: P2 turn
    begin_activation(state, p2a)
    end_activation(state)
    # activation_index 2: P1 turn
    begin_activation(state, p1b)
    end_activation(state)
    # activation_index 3: P2 turn
    begin_activation(state, p2b)
    end_activation(state)

    assert state.phase == Phase.ROUND_START


def test_end_activation_increments_round_number_after_4():
    state = _setup_through_activation()
    p1a = state.team1_units[0].unit_id
    p1b = state.team1_units[1].unit_id
    p2a = state.team2_units[0].unit_id
    p2b = state.team2_units[1].unit_id

    initial_round = state.round_number
    begin_activation(state, p1a); end_activation(state)
    begin_activation(state, p2a); end_activation(state)
    begin_activation(state, p1b); end_activation(state)
    begin_activation(state, p2b); end_activation(state)

    assert state.round_number == initial_round + 1


def test_end_activation_works_without_move_or_act():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    begin_activation(state, uid)
    # Don't move or act — just end
    end_activation(state)
    assert state.active_unit_id is None


def test_end_activation_raises_wrong_phase():
    state = _setup_through_round_start()
    with pytest.raises(ValueError):
        end_activation(state)


def test_end_activation_raises_no_active_unit():
    state = _setup_through_activation()
    with pytest.raises(ValueError):
        end_activation(state)


# ---------------------------------------------------------------------------
# Part 2: do_drop_item Tests
# ---------------------------------------------------------------------------

def _setup_item_drop_state(seed=42):
    """Set up state in ITEM_DROP phase with a pending drop."""
    state = _setup_through_activation(seed=seed)
    uid = state.team1_units[0].unit_id
    unit = get_unit(state, uid)
    # Give unit a carried item
    unit.carrying_item = "item_heal"
    # Place unit one step away from a clear item square (avoid obstacles)
    src_coord = Coordinate(col=4, row=2)
    item_coord = Coordinate(col=5, row=2)  # clear square adjacent to src
    state.board.unit_positions[uid] = src_coord
    state.board.item_positions[item_coord] = "item_atk"
    begin_activation(state, uid)
    state.movement_roll = 6
    # Move onto item square — triggers swap pickup → ITEM_DROP
    do_move(state, item_coord)
    return state, uid


def test_do_drop_item_places_item_on_valid_square():
    state, uid = _setup_item_drop_state()
    if state.phase != Phase.ITEM_DROP:
        pytest.skip("Item drop not triggered (no valid drop squares or no swap needed)")
    from dice_rangers.items import get_valid_drop_squares
    valid = get_valid_drop_squares(state.board, state.pending_drop_coord)
    if not valid:
        pytest.skip("No valid drop squares available")
    drop_coord = next(iter(valid))
    do_drop_item(state, drop_coord)
    assert drop_coord in state.board.item_positions


def test_do_drop_item_clears_pending_state():
    state, uid = _setup_item_drop_state()
    if state.phase != Phase.ITEM_DROP:
        pytest.skip("Item drop not triggered")
    from dice_rangers.items import get_valid_drop_squares
    valid = get_valid_drop_squares(state.board, state.pending_drop_coord)
    if not valid:
        pytest.skip("No valid drop squares available")
    drop_coord = next(iter(valid))
    do_drop_item(state, drop_coord)
    assert state.pending_drop_item is None
    assert state.pending_drop_coord is None


def test_do_drop_item_returns_to_activation():
    state, uid = _setup_item_drop_state()
    if state.phase != Phase.ITEM_DROP:
        pytest.skip("Item drop not triggered")
    from dice_rangers.items import get_valid_drop_squares
    valid = get_valid_drop_squares(state.board, state.pending_drop_coord)
    if not valid:
        pytest.skip("No valid drop squares available")
    drop_coord = next(iter(valid))
    do_drop_item(state, drop_coord)
    assert state.phase == Phase.ACTIVATION


def test_do_drop_item_raises_invalid_square():
    state = _setup_through_activation()
    # Manually set up ITEM_DROP phase
    state.phase = Phase.ITEM_DROP
    state.pending_drop_item = "item_heal"
    state.pending_drop_coord = Coordinate(col=4, row=4)
    # Use a far-away coord that's not adjacent
    with pytest.raises(ValueError):
        do_drop_item(state, Coordinate(col=0, row=0))


def test_do_drop_item_raises_wrong_phase():
    state = _setup_through_activation()
    with pytest.raises(ValueError):
        do_drop_item(state, Coordinate(col=0, row=0))


# ---------------------------------------------------------------------------
# Part 2: Action Order Flexibility Tests
# ---------------------------------------------------------------------------

def test_attack_then_move():
    state, p1_uid, p2_uid = _setup_adjacent_combat()
    # Act first
    do_attack(state, p2_uid)
    # Then move (if not in VICTORY)
    if state.phase == Phase.ACTIVATION:
        src = state.board.unit_positions[p1_uid]
        dest = Coordinate(col=src.col, row=max(0, src.row - 1))
        if dest != src:
            do_move(state, dest)
            assert get_unit(state, p1_uid).has_moved is True


def test_move_then_attack():
    state, p1_uid, p2_uid = _setup_adjacent_combat()
    # Move first (to same row, different col if possible)
    src = state.board.unit_positions[p1_uid]
    dest = Coordinate(col=max(0, src.col - 1), row=src.row)
    if dest != src and state.board.is_passable(dest):
        do_move(state, dest)
    # Then attack
    do_attack(state, p2_uid)
    assert get_unit(state, p1_uid).has_acted is True


def test_move_only_then_end():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    begin_activation(state, uid)
    src = state.board.unit_positions[uid]
    dest = Coordinate(col=src.col, row=src.row + 1)
    do_move(state, dest)
    end_activation(state)
    assert state.active_unit_id is None


def test_attack_only_then_end():
    state, p1_uid, p2_uid = _setup_adjacent_combat()
    do_attack(state, p2_uid)
    if state.phase == Phase.ACTIVATION:
        end_activation(state)
        assert state.active_unit_id is None


def test_skip_everything_and_end():
    state = _setup_through_activation()
    uid = state.team1_units[0].unit_id
    begin_activation(state, uid)
    do_skip_action(state)
    end_activation(state)
    assert state.active_unit_id is None


# ---------------------------------------------------------------------------
# Part 2: Integration Test
# ---------------------------------------------------------------------------

def test_partial_round_integration():
    """Seeded test: ROUND_START → event → P1 activate → move → attack P2 → end → P2 activate → move → end."""
    state = _setup_through_round_start(seed=7)

    # Round start
    event = resolve_round_start(state)
    assert state.phase == Phase.ACTIVATION
    assert state.activation_index == 0

    p1_uid = state.team1_units[0].unit_id
    p2_uid = state.team2_units[0].unit_id

    # Place units adjacent for combat
    state.board.unit_positions[p1_uid] = Coordinate(col=4, row=3)
    state.board.unit_positions[p2_uid] = Coordinate(col=4, row=4)

    # P1 activates
    roll = begin_activation(state, p1_uid)
    assert 1 <= roll <= 6
    assert state.active_unit_id == p1_uid

    # P1 attacks P2 (already adjacent, no move needed)
    initial_morale = state.team2_morale
    result = do_attack(state, p2_uid)
    if state.phase != Phase.VICTORY:
        assert state.team2_morale == max(0, initial_morale - result.net_damage)

    # End P1 activation
    if state.phase == Phase.ACTIVATION:
        end_activation(state)
        assert state.last_activated[1] == p1_uid
        assert state.activation_index == 1

    # P2 activates (activation_index=1 → team 2)
    if state.phase == Phase.ACTIVATION:
        roll2 = begin_activation(state, p2_uid)
        assert 1 <= roll2 <= 6

        # P2 moves one step
        src = state.board.unit_positions[p2_uid]
        dest = Coordinate(col=src.col, row=max(0, src.row - 1))
        if dest != src and state.board.is_passable(dest):
            do_move(state, dest)

        end_activation(state)
        assert state.last_activated[2] == p2_uid
        assert state.activation_index == 2
        assert state.phase == Phase.ACTIVATION  # 2 more activations remain


# ===========================================================================
# Part 3: Query / Helper Function Tests
# ===========================================================================




# ---------------------------------------------------------------------------
# Helpers for Part 3
# ---------------------------------------------------------------------------

def _setup_activation_state(seed=42) -> GameState:
    """Return a state in ACTIVATION phase with units on the board."""
    state = _setup_through_round_start(seed=seed)
    resolve_round_start(state)
    return state


def _place_units_adjacent(state: GameState) -> tuple[str, str]:
    """Place p1 unit at D4 and p2 unit at D5 (adjacent). Return (p1_uid, p2_uid)."""
    p1_uid = state.team1_units[0].unit_id
    p2_uid = state.team2_units[0].unit_id
    state.board.unit_positions[p1_uid] = Coordinate(col=3, row=3)
    state.board.unit_positions[p2_uid] = Coordinate(col=3, row=4)
    return p1_uid, p2_uid


# ---------------------------------------------------------------------------
# get_current_team
# ---------------------------------------------------------------------------

def test_get_current_team_returns_1_when_index_0():
    state = _setup_activation_state()
    state.activation_index = 0
    assert get_current_team(state) == 1


def test_get_current_team_returns_1_when_index_2():
    state = _setup_activation_state()
    state.activation_index = 2
    assert get_current_team(state) == 1


def test_get_current_team_returns_2_when_index_1():
    state = _setup_activation_state()
    state.activation_index = 1
    assert get_current_team(state) == 2


def test_get_current_team_returns_2_when_index_3():
    state = _setup_activation_state()
    state.activation_index = 3
    assert get_current_team(state) == 2


# ---------------------------------------------------------------------------
# get_team_morale
# ---------------------------------------------------------------------------

def test_get_team_morale_team1():
    state = _setup_activation_state()
    state.team1_morale = 15
    assert get_team_morale(state, 1) == 15


def test_get_team_morale_team2():
    state = _setup_activation_state()
    state.team2_morale = 12
    assert get_team_morale(state, 2) == 12


def test_get_team_morale_invalid_raises():
    state = _setup_activation_state()
    with pytest.raises(ValueError):
        get_team_morale(state, 3)


# ---------------------------------------------------------------------------
# get_valid_actions
# ---------------------------------------------------------------------------

def test_get_valid_actions_all_false_wrong_phase():
    state = _setup_through_round_start()
    # In ROUND_START phase — not ACTIVATION
    actions = get_valid_actions(state)
    assert actions == {
        "move": False,
        "attack": False,
        "use_item": False,
        "skip": False,
        "end_turn": False,
    }


def test_get_valid_actions_all_false_no_active_unit():
    state = _setup_activation_state()
    assert state.active_unit_id is None
    actions = get_valid_actions(state)
    assert actions == {
        "move": False,
        "attack": False,
        "use_item": False,
        "skip": False,
        "end_turn": False,
    }


def test_get_valid_actions_move_true_before_move():
    state = _setup_activation_state()
    p1_uid, _ = _place_units_adjacent(state)
    begin_activation(state, p1_uid)
    actions = get_valid_actions(state)
    assert actions["move"] is True


def test_get_valid_actions_move_false_after_move():
    state = _setup_activation_state()
    p1_uid = state.team1_units[0].unit_id
    p2_uid = state.team2_units[0].unit_id
    # Use a clear area of the board (bottom-right corner, away from seed=42 obstacles)
    state.board.unit_positions[p1_uid] = Coordinate(col=6, row=6)
    state.board.unit_positions[p2_uid] = Coordinate(col=6, row=7)
    begin_activation(state, p1_uid)
    state.movement_roll = 2
    dest = Coordinate(col=6, row=5)
    do_move(state, dest)
    actions = get_valid_actions(state)
    assert actions["move"] is False


def test_get_valid_actions_attack_true_when_enemy_adjacent():
    state = _setup_activation_state()
    p1_uid, _ = _place_units_adjacent(state)
    begin_activation(state, p1_uid)
    actions = get_valid_actions(state)
    assert actions["attack"] is True


def test_get_valid_actions_attack_false_no_enemy_in_range():
    state = _setup_activation_state()
    p1_uid = state.team1_units[0].unit_id
    p2_uid = state.team2_units[0].unit_id
    # Place units far apart
    state.board.unit_positions[p1_uid] = Coordinate(col=0, row=0)
    state.board.unit_positions[p2_uid] = Coordinate(col=7, row=7)
    begin_activation(state, p1_uid)
    actions = get_valid_actions(state)
    assert actions["attack"] is False


def test_get_valid_actions_use_item_true_when_carrying():
    state = _setup_activation_state()
    p1_uid, _ = _place_units_adjacent(state)
    unit = get_unit(state, p1_uid)
    unit.carrying_item = "item_heal"
    begin_activation(state, p1_uid)
    actions = get_valid_actions(state)
    assert actions["use_item"] is True


def test_get_valid_actions_use_item_false_when_not_carrying():
    state = _setup_activation_state()
    p1_uid, _ = _place_units_adjacent(state)
    unit = get_unit(state, p1_uid)
    unit.carrying_item = None
    begin_activation(state, p1_uid)
    actions = get_valid_actions(state)
    assert actions["use_item"] is False


def test_get_valid_actions_skip_true_before_acted():
    state = _setup_activation_state()
    p1_uid, _ = _place_units_adjacent(state)
    begin_activation(state, p1_uid)
    actions = get_valid_actions(state)
    assert actions["skip"] is True


def test_get_valid_actions_skip_false_after_acted():
    state = _setup_activation_state()
    p1_uid, _ = _place_units_adjacent(state)
    begin_activation(state, p1_uid)
    do_skip_action(state)
    actions = get_valid_actions(state)
    assert actions["skip"] is False


def test_get_valid_actions_end_turn_always_true():
    state = _setup_activation_state()
    p1_uid, _ = _place_units_adjacent(state)
    begin_activation(state, p1_uid)
    # Before and after acting
    assert get_valid_actions(state)["end_turn"] is True
    do_skip_action(state)
    assert get_valid_actions(state)["end_turn"] is True


# ---------------------------------------------------------------------------
# get_attackable_targets
# ---------------------------------------------------------------------------

def test_get_attackable_targets_melee_range():
    state = _setup_activation_state()
    p1_uid, p2_uid = _place_units_adjacent(state)
    begin_activation(state, p1_uid)
    targets = get_attackable_targets(state)
    assert p2_uid in targets


def test_get_attackable_targets_ranged_range_with_los():
    state = _setup_activation_state()
    p1_uid = state.team1_units[0].unit_id
    p2_uid = state.team2_units[0].unit_id
    # Place 2 squares apart (ranged range), clear LOS
    state.board.unit_positions[p1_uid] = Coordinate(col=3, row=3)
    state.board.unit_positions[p2_uid] = Coordinate(col=3, row=5)
    begin_activation(state, p1_uid)
    targets = get_attackable_targets(state)
    assert p2_uid in targets


def test_get_attackable_targets_excludes_blocked_by_obstacle():
    state = _setup_activation_state()
    p1_uid = state.team1_units[0].unit_id
    p2_uid = state.team2_units[0].unit_id
    # Place 2 squares apart with obstacle in between (blocking LOS)
    state.board.unit_positions[p1_uid] = Coordinate(col=3, row=3)
    state.board.unit_positions[p2_uid] = Coordinate(col=3, row=5)
    state.board.obstacles.add(Coordinate(col=3, row=4))
    begin_activation(state, p1_uid)
    targets = get_attackable_targets(state)
    assert p2_uid not in targets


def test_get_attackable_targets_excludes_out_of_range():
    state = _setup_activation_state()
    p1_uid = state.team1_units[0].unit_id
    p2_uid = state.team2_units[0].unit_id
    state.board.unit_positions[p1_uid] = Coordinate(col=0, row=0)
    state.board.unit_positions[p2_uid] = Coordinate(col=7, row=7)
    begin_activation(state, p1_uid)
    targets = get_attackable_targets(state)
    assert p2_uid not in targets


def test_get_attackable_targets_empty_no_active_unit():
    state = _setup_activation_state()
    assert get_attackable_targets(state) == []


def test_get_attackable_targets_excludes_friendly():
    state = _setup_activation_state()
    p1_uid = state.team1_units[0].unit_id
    p1b_uid = state.team1_units[1].unit_id
    # Place both team1 units adjacent
    state.board.unit_positions[p1_uid] = Coordinate(col=3, row=3)
    state.board.unit_positions[p1b_uid] = Coordinate(col=3, row=4)
    begin_activation(state, p1_uid)
    targets = get_attackable_targets(state)
    assert p1b_uid not in targets


# ---------------------------------------------------------------------------
# get_reachable_squares
# ---------------------------------------------------------------------------

def test_get_reachable_squares_returns_correct_set():
    state = _setup_activation_state()
    p1_uid, _ = _place_units_adjacent(state)
    # Force movement_roll manually after begin_activation
    begin_activation(state, p1_uid)
    state.movement_roll = 2
    squares = get_reachable_squares(state)
    assert len(squares) > 0
    # All squares should be within 2 orthogonal steps of D4 (col=3, row=3)
    start = Coordinate(col=3, row=3)
    for sq in squares:
        assert abs(sq.col - start.col) + abs(sq.row - start.row) <= 2


def test_get_reachable_squares_excludes_obstacles():
    state = _setup_activation_state()
    p1_uid = state.team1_units[0].unit_id
    state.board.unit_positions[p1_uid] = Coordinate(col=3, row=3)
    # Remove p2 from board to avoid blocking
    p2_uid = state.team2_units[0].unit_id
    state.board.unit_positions.pop(p2_uid, None)
    begin_activation(state, p1_uid)
    state.movement_roll = 1
    # Place obstacle directly above
    obs = Coordinate(col=3, row=2)
    state.board.obstacles.add(obs)
    squares = get_reachable_squares(state)
    assert obs not in squares


def test_get_reachable_squares_empty_when_already_moved():
    state = _setup_activation_state()
    p1_uid = state.team1_units[0].unit_id
    p2_uid = state.team2_units[0].unit_id
    # Use a clear area of the board
    state.board.unit_positions[p1_uid] = Coordinate(col=6, row=6)
    state.board.unit_positions[p2_uid] = Coordinate(col=6, row=7)
    begin_activation(state, p1_uid)
    state.movement_roll = 2
    dest = Coordinate(col=6, row=5)
    do_move(state, dest)
    squares = get_reachable_squares(state)
    assert squares == set()


def test_get_reachable_squares_empty_no_active_unit():
    state = _setup_activation_state()
    assert get_reachable_squares(state) == set()


def test_get_reachable_squares_empty_when_movement_roll_none():
    state = _setup_activation_state()
    p1_uid, _ = _place_units_adjacent(state)
    begin_activation(state, p1_uid)
    state.movement_roll = None
    assert get_reachable_squares(state) == set()


# ---------------------------------------------------------------------------
# get_drop_squares
# ---------------------------------------------------------------------------

def test_get_drop_squares_returns_empty_when_not_item_drop_phase():
    state = _setup_activation_state()
    assert get_drop_squares(state) == []


def test_get_drop_squares_returns_valid_squares_item_drop_phase():
    state = _setup_activation_state()
    p1_uid = state.team1_units[0].unit_id
    # Place unit and an item on the board
    unit_coord = Coordinate(col=3, row=3)
    item_coord = Coordinate(col=3, row=4)
    state.board.unit_positions[p1_uid] = unit_coord
    state.board.item_positions[item_coord] = "item_heal"
    # Give unit an item so pickup triggers a swap
    unit = get_unit(state, p1_uid)
    unit.carrying_item = "item_atk"
    # Manually set ITEM_DROP phase state
    state.phase = Phase.ITEM_DROP
    state.pending_drop_item = "item_atk"
    state.pending_drop_coord = item_coord
    state.active_unit_id = p1_uid
    drops = get_drop_squares(state)
    assert isinstance(drops, list)
    assert len(drops) > 0


# ---------------------------------------------------------------------------
# get_choosable_units
# ---------------------------------------------------------------------------

def test_get_choosable_units_returns_both_when_no_last_activated():
    state = _setup_activation_state()
    state.last_activated = {1: None, 2: None}
    choosable = get_choosable_units(state)
    p1_ids = [u.unit_id for u in state.team1_units]
    for uid in p1_ids:
        assert uid in choosable


def test_get_choosable_units_excludes_last_activated():
    state = _setup_activation_state()
    p1_uid = state.team1_units[0].unit_id
    p1b_uid = state.team1_units[1].unit_id
    state.last_activated[1] = p1_uid
    choosable = get_choosable_units(state)
    assert p1_uid not in choosable
    assert p1b_uid in choosable


def test_get_choosable_units_empty_when_activation_in_progress():
    state = _setup_activation_state()
    p1_uid, _ = _place_units_adjacent(state)
    begin_activation(state, p1_uid)
    assert get_choosable_units(state) == []


def test_get_choosable_units_empty_when_not_activation_phase():
    state = _setup_through_round_start()
    assert get_choosable_units(state) == []


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------

def test_query_helpers_integration_seeded():
    """Seeded integration: verify query helpers update correctly."""
    state = _setup_activation_state(seed=99)

    # Place units adjacent for combat
    p1_uid = state.team1_units[0].unit_id
    p2_uid = state.team2_units[0].unit_id
    state.board.unit_positions[p1_uid] = Coordinate(col=4, row=3)
    state.board.unit_positions[p2_uid] = Coordinate(col=4, row=4)

    # Before activation: no choosable units should be active_unit_id
    assert state.active_unit_id is None
    choosable = get_choosable_units(state)
    assert p1_uid in choosable

    # Verify team morale via helper
    assert get_team_morale(state, 1) == state.team1_morale
    assert get_team_morale(state, 2) == state.team2_morale

    # Begin activation
    begin_activation(state, p1_uid)
    assert get_current_team(state) == 1

    # Actions: move should be available, end_turn always True
    actions = get_valid_actions(state)
    assert actions["move"] is True
    assert actions["end_turn"] is True

    # Reachable squares should be non-empty
    squares = get_reachable_squares(state)
    assert len(squares) > 0

    # Attack should be available (p2 is adjacent)
    assert actions["attack"] is True
    assert p2_uid in get_attackable_targets(state)

    # Attack p2
    initial_morale = get_team_morale(state, 2)
    result = do_attack(state, p2_uid)

    if state.phase != Phase.VICTORY:
        new_morale = get_team_morale(state, 2)
        assert new_morale == max(0, initial_morale - result.net_damage)

        # After acting, skip/attack/use_item should be False
        actions_after = get_valid_actions(state)
        assert actions_after["skip"] is False
        assert actions_after["attack"] is False
        assert actions_after["end_turn"] is True

        end_activation(state)
        # After ending, no active unit → all False
        actions_ended = get_valid_actions(state)
        assert actions_ended == {
            "move": False,
            "attack": False,
            "use_item": False,
            "skip": False,
            "end_turn": False,
        }
