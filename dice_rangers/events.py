"""Board events system — random item spawning during play."""

from __future__ import annotations

from dataclasses import dataclass

from dice_rangers.board import Board, Coordinate
from dice_rangers.constants import EVENT_DIE
from dice_rangers.dice import DiceRoller

# ---------------------------------------------------------------------------
# Event type mapping
# ---------------------------------------------------------------------------

# Maps (low, high) inclusive roll range -> (event_type, item_id)
_EVENT_TABLE = [
    (1, 2, "nothing",    None),
    (3, 4, "spawn_heal", "item_heal"),
    (5, 6, "spawn_atk",  "item_atk"),
    (7, 8, "spawn_def",  "item_def"),
]


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class BoardEvent:
    event_roll: int
    event_type: str
    spawn_coord: Coordinate | None
    item_id: str | None


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def resolve_board_event(board: Board, roller: DiceRoller) -> BoardEvent:
    """Roll for a board event and apply it.

    Rolls 1d8 to determine event type. If an item spawns, rolls 2d8 for
    coordinates, re-rolling until an empty square is found. If the board is
    completely full, no item spawns.

    Returns:
        BoardEvent describing what happened.
    """
    event_roll = roller.roll(EVENT_DIE)

    # Determine event type from roll
    event_type = "nothing"
    item_id: str | None = None
    for low, high, etype, eid in _EVENT_TABLE:
        if low <= event_roll <= high:
            event_type = etype
            item_id = eid
            break

    if event_type == "nothing" or item_id is None:
        return BoardEvent(
            event_roll=event_roll,
            event_type=event_type,
            spawn_coord=None,
            item_id=None,
        )

    # Collect all empty squares on the board
    from dice_rangers.constants import GRID_SIZE
    all_coords = [
        Coordinate(col=c, row=r)
        for r in range(GRID_SIZE)
        for c in range(GRID_SIZE)
    ]
    empty_squares = [coord for coord in all_coords if board.is_empty(coord)]

    if not empty_squares:
        # Board is completely full — no spawn
        return BoardEvent(
            event_roll=event_roll,
            event_type=event_type,
            spawn_coord=None,
            item_id=None,
        )

    # Roll 2d8 for spawn coordinate, re-rolling until empty square found
    spawn_coord: Coordinate | None = None
    while spawn_coord is None:
        col_roll, row_roll = roller.roll_2d8()
        candidate = Coordinate(col=col_roll - 1, row=row_roll - 1)
        if board.is_empty(candidate):
            spawn_coord = candidate

    board.item_positions[spawn_coord] = item_id

    return BoardEvent(
        event_roll=event_roll,
        event_type=event_type,
        spawn_coord=spawn_coord,
        item_id=item_id,
    )
