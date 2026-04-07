"""Item spawning, pickup, and usage logic."""

from __future__ import annotations

from dataclasses import dataclass

from dice_rangers.board import Board, Coordinate
from dice_rangers.constants import ATK_BOOST, DEF_BOOST, HEAL_AMOUNT, MAX_MORALE
from dice_rangers.units import Unit

# ---------------------------------------------------------------------------
# Item type definitions
# ---------------------------------------------------------------------------

ITEM_TYPES: dict[str, dict] = {
    "item_heal": {"name": "Healing Potion", "effect": "heal",      "value": HEAL_AMOUNT},
    "item_atk":  {"name": "Attack Boost",   "effect": "atk_boost", "value": ATK_BOOST},
    "item_def":  {"name": "Defense Boost",  "effect": "def_boost", "value": DEF_BOOST},
}

# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PickupResult:
    picked_up: str
    dropped: str | None
    needs_drop_location: bool


@dataclass
class UseItemResult:
    item_used: str
    new_morale: int
    buff_activated: str | None


# ---------------------------------------------------------------------------
# Pickup
# ---------------------------------------------------------------------------


def pickup_item(board: Board, unit: Unit) -> PickupResult:
    """Pick up an item at the unit's current position.

    Raises:
        ValueError: If the unit has no board position or is not on an item square.
    """
    unit_coord = board.unit_positions.get(unit.unit_id)
    if unit_coord is None:
        raise ValueError(f"Unit {unit.unit_id!r} has no position on the board.")
    if unit_coord not in board.item_positions:
        raise ValueError(
            f"No item at {unit_coord.to_label()} for unit {unit.unit_id!r} to pick up."
        )

    new_item_id = board.item_positions[unit_coord]

    if unit.carrying_item is None:
        # Simple pickup
        unit.carrying_item = new_item_id
        del board.item_positions[unit_coord]
        unit.has_acted = True
        return PickupResult(picked_up=new_item_id, dropped=None, needs_drop_location=False)
    else:
        # Swap: drop old item, pick up new one
        old_item_id = unit.carrying_item
        unit.carrying_item = new_item_id
        del board.item_positions[unit_coord]
        unit.has_acted = True
        return PickupResult(
            picked_up=new_item_id,
            dropped=old_item_id,
            needs_drop_location=True,
        )


# ---------------------------------------------------------------------------
# Dropping
# ---------------------------------------------------------------------------


def get_valid_drop_squares(board: Board, coord: Coordinate) -> list[Coordinate]:
    """Return adjacent squares that are completely empty (no obstacle, unit, or item)."""
    return [sq for sq in board.get_adjacent_squares(coord) if board.is_empty(sq)]


def drop_item(board: Board, item_id: str, coord: Coordinate) -> None:
    """Place an item on an empty square.

    Raises:
        ValueError: If the square is not empty.
    """
    if not board.is_empty(coord):
        raise ValueError(f"Cannot drop item on occupied square {coord.to_label()}.")
    board.item_positions[coord] = item_id


# ---------------------------------------------------------------------------
# Can-move-onto check
# ---------------------------------------------------------------------------


def can_move_onto_item_square(board: Board, unit: Unit, coord: Coordinate) -> bool:
    """Return True if the unit can move onto coord (which may have an item).

    If the unit is already carrying an item and the destination has an item,
    there must be at least one valid drop square adjacent to coord.
    """
    if coord in board.item_positions and unit.carrying_item is not None:
        return len(get_valid_drop_squares(board, coord)) > 0
    return True


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------


def use_item(unit: Unit, team_morale: int) -> UseItemResult:
    """Use the item the unit is carrying.

    Raises:
        ValueError: If the unit has no item.
    """
    if unit.carrying_item is None:
        raise ValueError(f"Unit {unit.unit_id!r} has no item to use.")

    item_id = unit.carrying_item
    effect = ITEM_TYPES[item_id]["effect"]

    new_morale = team_morale
    buff_activated: str | None = None

    if effect == "heal":
        new_morale = min(team_morale + HEAL_AMOUNT, MAX_MORALE)
    elif effect == "atk_boost":
        unit.atk_boost_active = True
        buff_activated = "atk_boost"
    elif effect == "def_boost":
        unit.def_boost_active = True
        buff_activated = "def_boost"

    unit.carrying_item = None
    unit.has_acted = True

    return UseItemResult(
        item_used=item_id,
        new_morale=new_morale,
        buff_activated=buff_activated,
    )
