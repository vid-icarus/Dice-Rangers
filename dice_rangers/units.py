"""Unit data, movement, and combat logic."""

from __future__ import annotations

from dataclasses import dataclass

from dice_rangers.board import Board, Coordinate
from dice_rangers.constants import (
    ATK_BOOST,
    DEF_BOOST,
    DEFENSE_DIE,
    MELEE_DAMAGE_DIE,
    RANGED_DAMAGE_DIE,
)
from dice_rangers.dice import DiceRoller

# ---------------------------------------------------------------------------
# Valid customization IDs
# ---------------------------------------------------------------------------

VALID_RACES: dict[str, list[str]] = {
    "race_bird":   ["eagle", "parrot", "toucan", "owl", "penguin"],
    "race_cat":    ["tabby", "siamese", "calico", "black_cat", "persian"],
    "race_spider": ["garden", "jumping", "tarantula", "orb_weaver"],
    "race_dragon": ["fire", "ice", "forest", "baby"],
    "race_dino":   ["trex", "raptor", "triceratops", "stego"],
    "race_robot":  ["classic", "mech", "drone", "retro"],
}

VALID_OUTFITS: set[str] = {
    "outfit_warrior", "outfit_wizard", "outfit_rogue",
    "outfit_ranger", "outfit_cleric", "outfit_knight",
}

VALID_COLORS: dict[str, str] = {
    "color_red":     "#FF0000",
    "color_orange":  "#FF8800",
    "color_yellow":  "#FFFF00",
    "color_lime":    "#88FF00",
    "color_green":   "#00CC00",
    "color_teal":    "#00CCAA",
    "color_cyan":    "#00CCFF",
    "color_blue":    "#0044FF",
    "color_indigo":  "#4400CC",
    "color_purple":  "#8800CC",
    "color_pink":    "#FF44CC",
    "color_hotpink": "#FF0088",
    "color_white":   "#FFFFFF",
    "color_ltgray":  "#AAAAAA",
    "color_dkgray":  "#555555",
    "color_black":   "#222222",
}

VALID_ATTACK_FLAVORS: set[str] = {
    "atk_sword", "atk_bow", "atk_magic", "atk_hugs", "atk_hearts",
    "atk_butterflies", "atk_sparkle", "atk_laser", "atk_slime",
}

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Customization:
    race: str
    variant: str
    outfit: str
    primary_color: str
    secondary_color: str
    attack_flavor: str


@dataclass
class Unit:
    unit_id: str
    team: int
    customization: Customization
    carrying_item: str | None
    atk_boost_active: bool
    def_boost_active: bool
    has_moved: bool
    has_acted: bool


@dataclass
class AttackResult:
    attack_roll: int
    attack_bonus: int
    defense_roll: int
    defense_bonus: int
    net_damage: int
    is_melee: bool
    attacker_id: str
    defender_id: str


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_customization(customization: Customization) -> None:
    """Validate all fields of a Customization. Raises ValueError on failure."""
    if customization.race not in VALID_RACES:
        raise ValueError(f"Invalid race: {customization.race!r}")
    if customization.variant not in VALID_RACES[customization.race]:
        raise ValueError(
            f"Invalid variant {customization.variant!r} for race {customization.race!r}"
        )
    if customization.outfit not in VALID_OUTFITS:
        raise ValueError(f"Invalid outfit: {customization.outfit!r}")
    if customization.primary_color not in VALID_COLORS:
        raise ValueError(f"Invalid primary_color: {customization.primary_color!r}")
    if customization.secondary_color not in VALID_COLORS:
        raise ValueError(f"Invalid secondary_color: {customization.secondary_color!r}")
    if customization.attack_flavor not in VALID_ATTACK_FLAVORS:
        raise ValueError(f"Invalid attack_flavor: {customization.attack_flavor!r}")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_unit(unit_id: str, team: int, customization: Customization) -> Unit:
    """Create a new Unit after validating its customization.

    Raises:
        ValueError: If customization is invalid.
    """
    validate_customization(customization)
    return Unit(
        unit_id=unit_id,
        team=team,
        customization=customization,
        carrying_item=None,
        atk_boost_active=False,
        def_boost_active=False,
        has_moved=False,
        has_acted=False,
    )


# ---------------------------------------------------------------------------
# Movement
# ---------------------------------------------------------------------------


def move_unit(
    board: Board, unit: Unit, destination: Coordinate, max_steps: int
) -> None:
    """Move a unit to destination if reachable within max_steps.

    Raises:
        ValueError: If destination is not reachable.
    """
    current_pos = board.unit_positions.get(unit.unit_id)
    if current_pos is None:
        raise ValueError(f"Unit {unit.unit_id!r} has no position on the board.")

    reachable = board.get_reachable_squares(current_pos, max_steps)
    if destination not in reachable:
        raise ValueError(
            f"Destination {destination.to_label()} is not reachable from "
            f"{current_pos.to_label()} within {max_steps} steps."
        )

    board.unit_positions[unit.unit_id] = destination
    unit.has_moved = True


# ---------------------------------------------------------------------------
# Combat
# ---------------------------------------------------------------------------


def _chebyshev(a: Coordinate, b: Coordinate) -> int:
    return max(abs(a.col - b.col), abs(a.row - b.row))


def can_attack(
    attacker_coord: Coordinate,
    defender_coord: Coordinate,
    board: Board,
) -> tuple[bool, bool]:
    """Determine if attacker can attack defender and whether it is melee.

    Returns:
        (can_attack, is_melee)
    """
    dist = _chebyshev(attacker_coord, defender_coord)
    if dist == 1:
        return (True, True)
    if 2 <= dist <= 3 and board.has_line_of_sight(attacker_coord, defender_coord):
        return (True, False)
    return (False, False)


def resolve_attack(
    attacker: Unit,
    defender: Unit,
    board: Board,
    roller: DiceRoller,
) -> AttackResult:
    """Resolve an attack between two units.

    Raises:
        ValueError: If attacker or defender has no board position, or if no
                    valid attack exists.
    """
    attacker_coord = board.unit_positions.get(attacker.unit_id)
    if attacker_coord is None:
        raise ValueError(f"Attacker {attacker.unit_id!r} has no position on the board.")
    defender_coord = board.unit_positions.get(defender.unit_id)
    if defender_coord is None:
        raise ValueError(f"Defender {defender.unit_id!r} has no position on the board.")

    ok, is_melee = can_attack(attacker_coord, defender_coord, board)
    if not ok:
        raise ValueError(
            f"No valid attack from {attacker_coord.to_label()}"
            f" to {defender_coord.to_label()}."
        )

    # Roll attack
    die = MELEE_DAMAGE_DIE if is_melee else RANGED_DAMAGE_DIE
    attack_roll = roller.roll(die)
    attack_bonus = 0
    if attacker.atk_boost_active:
        attack_bonus = ATK_BOOST
        attacker.atk_boost_active = False

    # Roll defense
    defense_roll = roller.roll(DEFENSE_DIE)
    defense_bonus = 0
    if defender.def_boost_active:
        defense_bonus = DEF_BOOST
        defender.def_boost_active = False

    net_damage = max(0, (attack_roll + attack_bonus) - (defense_roll + defense_bonus))
    attacker.has_acted = True

    return AttackResult(
        attack_roll=attack_roll,
        attack_bonus=attack_bonus,
        defense_roll=defense_roll,
        defense_bonus=defense_bonus,
        net_damage=net_damage,
        is_melee=is_melee,
        attacker_id=attacker.unit_id,
        defender_id=defender.unit_id,
    )


# ---------------------------------------------------------------------------
# Activation reset
# ---------------------------------------------------------------------------


def reset_activation(unit: Unit) -> None:
    """Reset per-activation flags at the start of a unit's turn."""
    unit.has_moved = False
    unit.has_acted = False
