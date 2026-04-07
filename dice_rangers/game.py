"""Core game loop & state management for Dice Rangers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from dice_rangers.board import Board, Coordinate
from dice_rangers.constants import (
    OBSTACLES_PER_PLAYER,
    P1_SPAWN_ROWS,
    P2_SPAWN_ROWS,
    STARTING_MORALE,
)
from dice_rangers.dice import DiceRoller
from dice_rangers.events import BoardEvent
from dice_rangers.units import Customization, Unit, create_unit


# ---------------------------------------------------------------------------
# Phase Enum
# ---------------------------------------------------------------------------


class Phase(Enum):
    P1_CUSTOMIZE = "p1_customize"
    P2_CUSTOMIZE = "p2_customize"
    OBSTACLE_PLACEMENT = "obstacle_placement"
    SPAWN_PLACEMENT = "spawn_placement"
    ROUND_START = "round_start"
    ACTIVATION = "activation"
    ITEM_DROP = "item_drop"
    VICTORY = "victory"


# ---------------------------------------------------------------------------
# GameState Dataclass
# ---------------------------------------------------------------------------


@dataclass
class GameState:
    phase: Phase
    board: Board
    roller: DiceRoller

    # Teams
    team1_morale: int
    team2_morale: int
    team1_units: list[Unit]
    team2_units: list[Unit]

    # Obstacle placement tracking
    obstacles_placed: int
    current_placer: int
    obstacle_roll: tuple[int, int] | None

    # Spawn placement tracking
    current_spawner: int
    units_spawned_this_player: int

    # Round tracking
    round_number: int
    activation_index: int
    last_activated: dict[int, str | None]

    # Current activation state
    active_unit_id: str | None
    movement_roll: int | None

    # Board event
    current_event: BoardEvent | None

    # Item drop state
    pending_drop_item: str | None
    pending_drop_coord: Coordinate | None

    # Victory
    winner: int | None


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def new_game(seed: int | None = None) -> GameState:
    """Create a fresh GameState ready for player 1 customization.

    Args:
        seed: Optional RNG seed for deterministic play/testing.

    Returns:
        A new GameState in P1_CUSTOMIZE phase.
    """
    return GameState(
        phase=Phase.P1_CUSTOMIZE,
        board=Board(),
        roller=DiceRoller(seed),
        team1_morale=STARTING_MORALE,
        team2_morale=STARTING_MORALE,
        team1_units=[],
        team2_units=[],
        obstacles_placed=0,
        current_placer=1,
        obstacle_roll=None,
        current_spawner=1,
        units_spawned_this_player=0,
        round_number=1,
        activation_index=0,
        last_activated={1: None, 2: None},
        active_unit_id=None,
        movement_roll=None,
        current_event=None,
        pending_drop_item=None,
        pending_drop_coord=None,
        winner=None,
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def get_unit(state: GameState, unit_id: str) -> Unit:
    """Find a unit by ID across both teams.

    Args:
        state: Current game state.
        unit_id: The unit's unique identifier.

    Returns:
        The matching Unit.

    Raises:
        ValueError: If no unit with that ID exists.
    """
    for unit in state.team1_units + state.team2_units:
        if unit.unit_id == unit_id:
            return unit
    raise ValueError(f"Unit not found: {unit_id!r}")


# ---------------------------------------------------------------------------
# Customization Phase
# ---------------------------------------------------------------------------


def submit_customization(
    state: GameState, unit_id: str, team: int, customization: Customization
) -> None:
    """Submit a unit customization for the current player.

    Args:
        state: Current game state.
        unit_id: Unique ID for the new unit.
        team: Which team (1 or 2) this unit belongs to.
        customization: The unit's cosmetic customization.

    Raises:
        ValueError: If the phase/team combination is invalid, or if the
                    customization is invalid.
    """
    # Phase guard
    if state.phase == Phase.P1_CUSTOMIZE and team != 1:
        raise ValueError(
            f"Expected team 1 during P1_CUSTOMIZE, got team {team}"
        )
    elif state.phase == Phase.P2_CUSTOMIZE and team != 2:
        raise ValueError(
            f"Expected team 2 during P2_CUSTOMIZE, got team {team}"
        )
    elif state.phase not in (Phase.P1_CUSTOMIZE, Phase.P2_CUSTOMIZE):
        raise ValueError(
            f"submit_customization called in wrong phase: {state.phase}"
        )

    # create_unit validates customization and raises ValueError on failure
    unit = create_unit(unit_id, team, customization)

    if team == 1:
        state.team1_units.append(unit)
        if len(state.team1_units) == 2:
            state.phase = Phase.P2_CUSTOMIZE
    else:
        state.team2_units.append(unit)
        if len(state.team2_units) == 2:
            state.phase = Phase.OBSTACLE_PLACEMENT
            state.current_placer = 1
            state.obstacles_placed = 0


# ---------------------------------------------------------------------------
# Obstacle Placement Phase
# ---------------------------------------------------------------------------


def roll_obstacle(state: GameState) -> tuple[int, int]:
    """Roll 2d8 to determine the target square for obstacle placement.

    Args:
        state: Current game state.

    Returns:
        A (col_roll, row_roll) tuple, each value in 1–8.

    Raises:
        ValueError: If not in OBSTACLE_PLACEMENT phase, or if a roll is
                    already pending (must place before rolling again).
    """
    if state.phase != Phase.OBSTACLE_PLACEMENT:
        raise ValueError(
            f"roll_obstacle called in wrong phase: {state.phase}"
        )
    if state.obstacle_roll is not None:
        raise ValueError(
            "Must place obstacle before rolling again"
        )
    result = state.roller.roll_2d8()
    state.obstacle_roll = result
    return result


def place_obstacle(state: GameState, coord: Coordinate) -> None:
    """Place an obstacle at the given coordinate.

    The coordinate must be the rolled square or adjacent to it.

    Args:
        state: Current game state.
        coord: Where to place the obstacle.

    Raises:
        ValueError: If not in OBSTACLE_PLACEMENT phase, no roll is pending,
                    the coordinate is not valid (not rolled/adjacent), or
                    board.place_obstacle raises (edge/occupied).
    """
    if state.phase != Phase.OBSTACLE_PLACEMENT:
        raise ValueError(
            f"place_obstacle called in wrong phase: {state.phase}"
        )
    if state.obstacle_roll is None:
        raise ValueError("Must roll before placing obstacle")

    col_roll, row_roll = state.obstacle_roll
    rolled_coord = Coordinate(col=col_roll - 1, row=row_roll - 1)

    # Validate coord is rolled square or adjacent
    adjacent = state.board.get_adjacent_squares(rolled_coord)
    if coord != rolled_coord and coord not in adjacent:
        raise ValueError(
            f"{coord.to_label()} is not the rolled square "
            f"({rolled_coord.to_label()}) or adjacent to it"
        )

    # Delegate edge/occupancy validation to board
    state.board.place_obstacle(coord)

    state.obstacles_placed += 1
    state.current_placer = 2 if state.current_placer == 1 else 1
    state.obstacle_roll = None

    total_obstacles = OBSTACLES_PER_PLAYER * 2
    if state.obstacles_placed == total_obstacles:
        state.phase = Phase.SPAWN_PLACEMENT
        state.current_spawner = 1
        state.units_spawned_this_player = 0


# ---------------------------------------------------------------------------
# Spawn Placement Phase
# ---------------------------------------------------------------------------

# Convert 1-indexed display rows from constants to 0-indexed sets
_P1_SPAWN_ROW_SET: frozenset[int] = frozenset(r - 1 for r in P1_SPAWN_ROWS)
_P2_SPAWN_ROW_SET: frozenset[int] = frozenset(r - 1 for r in P2_SPAWN_ROWS)


def place_unit_on_board(
    state: GameState, unit_id: str, coord: Coordinate
) -> None:
    """Place a unit on the board during the spawn placement phase.

    Args:
        state: Current game state.
        unit_id: ID of the unit to place.
        coord: Board coordinate to place the unit on.

    Raises:
        ValueError: If not in SPAWN_PLACEMENT phase, unit not found, unit
                    doesn't belong to current spawner, unit already placed,
                    coordinate outside spawn zone, or square not passable.
    """
    if state.phase != Phase.SPAWN_PLACEMENT:
        raise ValueError(
            f"place_unit_on_board called in wrong phase: {state.phase}"
        )

    unit = get_unit(state, unit_id)

    # Validate unit belongs to current spawner
    if unit.team != state.current_spawner:
        raise ValueError(
            f"Unit {unit_id!r} belongs to team {unit.team}, "
            f"but current spawner is team {state.current_spawner}"
        )

    # Validate unit not already placed
    if unit_id in state.board.unit_positions:
        raise ValueError(f"Unit {unit_id!r} is already on the board")

    # Validate spawn zone
    if state.current_spawner == 1:
        valid_rows = _P1_SPAWN_ROW_SET
    else:
        valid_rows = _P2_SPAWN_ROW_SET

    if coord.row not in valid_rows:
        raise ValueError(
            f"Coordinate {coord.to_label()} is outside spawn zone "
            f"for player {state.current_spawner}"
        )

    # Validate square is passable
    if not state.board.is_passable(coord):
        raise ValueError(
            f"Square {coord.to_label()} is not passable"
        )

    state.board.unit_positions[unit_id] = coord
    state.units_spawned_this_player += 1

    if state.units_spawned_this_player == 2:
        if state.current_spawner == 1:
            state.current_spawner = 2
            state.units_spawned_this_player = 0
        else:
            state.phase = Phase.ROUND_START


# ---------------------------------------------------------------------------
# Entry point (placeholder — replaced in a future hotfix)
# ---------------------------------------------------------------------------


def main() -> None:
    print("Dice Rangers v0.1.0 — Ready to battle!")
