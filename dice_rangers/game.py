"""Core game loop & state management for Dice Rangers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dice_rangers.board import Board, Coordinate
from dice_rangers.constants import (
    MOVEMENT_DIE,
    OBSTACLES_PER_PLAYER,
    P1_SPAWN_ROWS,
    P2_SPAWN_ROWS,
    STARTING_MORALE,
)
from dice_rangers.dice import DiceRoller
from dice_rangers.events import BoardEvent, resolve_board_event
from dice_rangers.items import (
    PickupResult,
    UseItemResult,
    can_move_onto_item_square,
    drop_item,
    get_valid_drop_squares,
    pickup_item,
    use_item,
)
from dice_rangers.units import (
    AttackResult,
    Customization,
    Unit,
    can_attack,
    create_unit,
    move_unit,
    reset_activation,
    resolve_attack,
)

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
# Round Start Phase
# ---------------------------------------------------------------------------


def resolve_round_start(state: GameState) -> BoardEvent:
    """Roll for a board event, reset activation index, advance to ACTIVATION.

    Raises:
        ValueError: If not in ROUND_START phase.
    """
    if state.phase != Phase.ROUND_START:
        raise ValueError(f"resolve_round_start called in wrong phase: {state.phase}")

    event = resolve_board_event(state.board, state.roller)
    state.current_event = event
    state.activation_index = 0
    state.phase = Phase.ACTIVATION
    return event


# ---------------------------------------------------------------------------
# Activation Phase
# ---------------------------------------------------------------------------


def begin_activation(state: GameState, unit_id: str) -> int:
    """Begin a unit's activation: validate, reset, roll movement.

    Args:
        state: Current game state.
        unit_id: The unit to activate.

    Returns:
        The movement roll (1–MOVEMENT_DIE).

    Raises:
        ValueError: If phase is wrong, unit is invalid, or alternation rule violated.
    """
    if state.phase != Phase.ACTIVATION:
        raise ValueError(f"begin_activation called in wrong phase: {state.phase}")
    if state.active_unit_id is not None:
        raise ValueError(
            f"Previous activation not ended (active_unit_id={state.active_unit_id!r})"
        )

    # Determine which team's turn it is
    team = 1 if state.activation_index % 2 == 0 else 2

    # Validate unit belongs to that team
    team_units = state.team1_units if team == 1 else state.team2_units
    team_unit_ids = {u.unit_id for u in team_units}
    if unit_id not in team_unit_ids:
        raise ValueError(
            f"Unit {unit_id!r} does not belong to team {team} "
            f"(activation_index={state.activation_index})"
        )

    # Validate unit has a board position
    if unit_id not in state.board.unit_positions:
        raise ValueError(f"Unit {unit_id!r} has no position on the board")

    # Alternation rule: can't activate same unit twice in a row
    if state.last_activated[team] is not None and state.last_activated[team] == unit_id:
        raise ValueError(
            f"Unit {unit_id!r} was last activated for team {team}; "
            "must activate the other unit"
        )

    unit = get_unit(state, unit_id)
    reset_activation(unit)

    roll = state.roller.roll(MOVEMENT_DIE)
    state.movement_roll = roll
    state.active_unit_id = unit_id
    return roll


def do_move(state: GameState, destination: Coordinate) -> PickupResult | None:
    """Move the active unit to destination, handling item pickup.

    Args:
        state: Current game state.
        destination: Target coordinate.

    Returns:
        PickupResult if an item was picked up, else None.

    Raises:
        ValueError: If phase wrong, no active unit, already moved, or destination
            invalid.
    """
    if state.phase != Phase.ACTIVATION:
        raise ValueError(f"do_move called in wrong phase: {state.phase}")
    if state.active_unit_id is None:
        raise ValueError("No active unit")

    unit = get_unit(state, state.active_unit_id)
    if unit.has_moved:
        raise ValueError(f"Unit {unit.unit_id!r} has already moved this activation")

    # Item-square check before moving
    if destination in state.board.item_positions:
        if not can_move_onto_item_square(state.board, unit, destination):
            raise ValueError(
                "Cannot move there: no valid drop square for current item"
            )

    # Move the unit (validates reachability, sets has_moved=True)
    move_unit(state.board, unit, destination, state.movement_roll)

    # Auto-pickup check
    if destination in state.board.item_positions:
        pickup_result = pickup_item(state.board, unit)
        if pickup_result.needs_drop_location:
            state.pending_drop_item = pickup_result.dropped
            state.pending_drop_coord = destination
            state.phase = Phase.ITEM_DROP
        return pickup_result

    return None


def do_attack(state: GameState, target_unit_id: str) -> AttackResult:
    """Attack a target unit.

    Args:
        state: Current game state.
        target_unit_id: The unit to attack.

    Returns:
        AttackResult with damage details.

    Raises:
        ValueError: If phase wrong, no active unit, already acted, or invalid target.
    """
    if state.phase != Phase.ACTIVATION:
        raise ValueError(f"do_attack called in wrong phase: {state.phase}")
    if state.active_unit_id is None:
        raise ValueError("No active unit")

    attacker = get_unit(state, state.active_unit_id)
    if attacker.has_acted:
        raise ValueError(f"Unit {attacker.unit_id!r} has already acted this activation")

    defender = get_unit(state, target_unit_id)
    if defender.team == attacker.team:
        raise ValueError(
            f"Cannot attack friendly unit {target_unit_id!r} "
            f"(same team {attacker.team})"
        )

    result = resolve_attack(attacker, defender, state.board, state.roller)

    # Apply damage to defender's team morale
    if defender.team == 1:
        state.team1_morale = max(0, state.team1_morale - result.net_damage)
    else:
        state.team2_morale = max(0, state.team2_morale - result.net_damage)

    # Win condition check (attacker's team wins if they reduce enemy to 0)
    if state.team1_morale <= 0:
        state.winner = 2
        state.phase = Phase.VICTORY
    elif state.team2_morale <= 0:
        state.winner = 1
        state.phase = Phase.VICTORY

    return result


def do_use_item(state: GameState) -> UseItemResult:
    """Use the active unit's carried item.

    Returns:
        UseItemResult with effect details.

    Raises:
        ValueError: If phase wrong, no active unit, already acted, or no item.
    """
    if state.phase != Phase.ACTIVATION:
        raise ValueError(f"do_use_item called in wrong phase: {state.phase}")
    if state.active_unit_id is None:
        raise ValueError("No active unit")

    unit = get_unit(state, state.active_unit_id)
    if unit.has_acted:
        raise ValueError(f"Unit {unit.unit_id!r} has already acted this activation")
    if unit.carrying_item is None:
        raise ValueError(f"Unit {unit.unit_id!r} is not carrying an item")

    morale = state.team1_morale if unit.team == 1 else state.team2_morale
    result = use_item(unit, morale)

    if unit.team == 1:
        state.team1_morale = result.new_morale
    else:
        state.team2_morale = result.new_morale

    return result


def do_skip_action(state: GameState) -> None:
    """Skip the active unit's action (sets has_acted=True).

    Raises:
        ValueError: If phase wrong, no active unit, or already acted.
    """
    if state.phase != Phase.ACTIVATION:
        raise ValueError(f"do_skip_action called in wrong phase: {state.phase}")
    if state.active_unit_id is None:
        raise ValueError("No active unit")

    unit = get_unit(state, state.active_unit_id)
    if unit.has_acted:
        raise ValueError(f"Unit {unit.unit_id!r} has already acted this activation")

    unit.has_acted = True


def end_activation(state: GameState) -> None:
    """End the current unit's activation and advance turn order.

    Raises:
        ValueError: If phase wrong or no active unit.
    """
    if state.phase != Phase.ACTIVATION:
        raise ValueError(f"end_activation called in wrong phase: {state.phase}")
    if state.active_unit_id is None:
        raise ValueError("No active unit to end")

    unit = get_unit(state, state.active_unit_id)
    state.last_activated[unit.team] = state.active_unit_id
    state.activation_index += 1
    state.active_unit_id = None
    state.movement_roll = None

    if state.activation_index >= 4:
        state.round_number += 1
        state.phase = Phase.ROUND_START
    # else: stays in ACTIVATION


# ---------------------------------------------------------------------------
# Item Drop Phase
# ---------------------------------------------------------------------------


def do_drop_item(state: GameState, drop_coord: Coordinate) -> None:
    """Drop the pending item at a valid adjacent square.

    Args:
        state: Current game state.
        drop_coord: Where to drop the item.

    Raises:
        ValueError: If phase wrong, no pending item, or invalid drop square.
    """
    if state.phase != Phase.ITEM_DROP:
        raise ValueError(f"do_drop_item called in wrong phase: {state.phase}")
    if state.pending_drop_item is None:
        raise ValueError("No pending item to drop")
    if state.pending_drop_coord is None:
        raise ValueError("No pending drop coordinate")

    valid_squares = get_valid_drop_squares(state.board, state.pending_drop_coord)
    if drop_coord not in valid_squares:
        raise ValueError(
            f"Drop coordinate {drop_coord.to_label()} is not a valid drop square"
        )

    drop_item(state.board, state.pending_drop_item, drop_coord)
    state.pending_drop_item = None
    state.pending_drop_coord = None
    state.phase = Phase.ACTIVATION



# ---------------------------------------------------------------------------
# Query / Helper Functions (read-only)
# ---------------------------------------------------------------------------

_ALL_FALSE_ACTIONS: dict[str, bool] = {
    "move": False,
    "attack": False,
    "use_item": False,
    "skip": False,
    "end_turn": False,
}


def get_current_team(state: GameState) -> int:
    """Return which team's turn it is (1 or 2) based on activation_index."""
    return 1 if state.activation_index % 2 == 0 else 2


def get_team_morale(state: GameState, team: int) -> int:
    """Return the morale for the given team (1 or 2).

    Raises:
        ValueError: If team is not 1 or 2.
    """
    if team == 1:
        return state.team1_morale
    if team == 2:
        return state.team2_morale
    raise ValueError(f"Invalid team number: {team!r}. Must be 1 or 2.")


def get_attackable_targets(state: GameState) -> list[str]:
    """Return list of enemy unit IDs the active unit can currently attack."""
    if state.phase != Phase.ACTIVATION or state.active_unit_id is None:
        return []

    active_unit = get_unit(state, state.active_unit_id)
    active_coord = state.board.unit_positions.get(state.active_unit_id)
    if active_coord is None:
        return []

    enemy_units = state.team2_units if active_unit.team == 1 else state.team1_units
    targets: list[str] = []
    for enemy in enemy_units:
        enemy_coord = state.board.unit_positions.get(enemy.unit_id)
        if enemy_coord is None:
            continue
        ok, _ = can_attack(active_coord, enemy_coord, state.board)
        if ok:
            targets.append(enemy.unit_id)
    return targets


def get_valid_actions(state: GameState) -> dict[str, bool]:
    """Return a dict of available actions for the active unit.

    Always returns all five keys. Returns all-False when not in ACTIVATION
    phase or no active unit.
    """
    if state.phase != Phase.ACTIVATION or state.active_unit_id is None:
        return dict(_ALL_FALSE_ACTIONS)

    unit = get_unit(state, state.active_unit_id)
    return {
        "move": not unit.has_moved,
        "attack": (
            not unit.has_acted and bool(get_attackable_targets(state))
        ),
        "use_item": not unit.has_acted and unit.carrying_item is not None,
        "skip": not unit.has_acted,
        "end_turn": True,
    }


def get_reachable_squares(state: GameState) -> set[Coordinate]:
    """Return the set of squares the active unit can move to."""
    if state.phase != Phase.ACTIVATION or state.active_unit_id is None:
        return set()

    unit = get_unit(state, state.active_unit_id)
    if unit.has_moved:
        return set()

    if state.movement_roll is None:
        return set()

    current_pos = state.board.unit_positions.get(state.active_unit_id)
    if current_pos is None:
        return set()

    candidates = state.board.get_reachable_squares(current_pos, state.movement_roll)
    # Filter out item squares where the unit cannot legally move (no drop location)
    return {
        coord for coord in candidates
        if can_move_onto_item_square(state.board, unit, coord)
    }


def get_drop_squares(state: GameState) -> list[Coordinate]:
    """Return valid squares where the pending item can be dropped."""
    if state.phase != Phase.ITEM_DROP or state.pending_drop_coord is None:
        return []
    return get_valid_drop_squares(state.board, state.pending_drop_coord)


def get_choosable_units(state: GameState) -> list[str]:
    """Return unit IDs the current team can activate."""
    if state.phase != Phase.ACTIVATION or state.active_unit_id is not None:
        return []

    team = get_current_team(state)
    team_units = state.team1_units if team == 1 else state.team2_units
    last = state.last_activated.get(team)

    choosable: list[str] = []
    for unit in team_units:
        if unit.unit_id not in state.board.unit_positions:
            continue
        if last is not None and unit.unit_id == last:
            continue
        choosable.append(unit.unit_id)
    return choosable
