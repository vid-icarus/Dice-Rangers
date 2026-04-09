"""Tests for units.py — unit creation, movement, and combat."""

import pytest

from dice_rangers.board import Board, Coordinate
from dice_rangers.dice import DiceRoller
from dice_rangers.units import (
    Customization,
    can_attack,
    create_unit,
    move_unit,
    reset_activation,
    resolve_attack,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_customization(**overrides):
    defaults = dict(
        race="race_bird",
        variant="eagle",
        outfit="outfit_warrior",
        primary_color="color_red",
        secondary_color="color_blue",
        attack_flavor="atk_sword",
    )
    defaults.update(overrides)
    return Customization(**defaults)


def make_unit(unit_id="p1_unit1", team=1, **overrides):
    return create_unit(unit_id, team, make_customization(**overrides))


# ---------------------------------------------------------------------------
# create_unit — valid
# ---------------------------------------------------------------------------

def test_create_unit_valid():
    unit = make_unit()
    assert unit.unit_id == "p1_unit1"
    assert unit.team == 1
    assert unit.carrying_item is None
    assert unit.atk_boost_active is False
    assert unit.def_boost_active is False
    assert unit.has_moved is False
    assert unit.has_acted is False


# ---------------------------------------------------------------------------
# create_unit — invalid customization
# ---------------------------------------------------------------------------

def test_create_unit_invalid_race():
    with pytest.raises(ValueError, match="race"):
        make_unit(race="race_unicorn")


def test_create_unit_invalid_variant():
    with pytest.raises(ValueError, match="variant"):
        make_unit(variant="phoenix")  # valid race_bird but invalid variant


def test_create_unit_invalid_outfit():
    with pytest.raises(ValueError, match="outfit"):
        make_unit(outfit="outfit_ninja")


def test_create_unit_invalid_color():
    with pytest.raises(ValueError, match="color"):
        make_unit(primary_color="color_mauve")


def test_create_unit_invalid_attack_flavor():
    with pytest.raises(ValueError, match="attack_flavor"):
        make_unit(attack_flavor="atk_punch")


# ---------------------------------------------------------------------------
# move_unit
# ---------------------------------------------------------------------------

def _board_with_unit(unit_id, coord):
    board = Board()
    board.unit_positions[unit_id] = coord
    return board


def test_move_unit_valid():
    unit = make_unit("u1")
    start = Coordinate(3, 3)
    dest = Coordinate(3, 5)  # 2 steps away
    board = _board_with_unit("u1", start)
    move_unit(board, unit, dest, max_steps=3)
    assert board.unit_positions["u1"] == dest
    assert unit.has_moved is True


def test_move_unit_out_of_range():
    unit = make_unit("u1")
    start = Coordinate(0, 0)
    dest = Coordinate(5, 5)  # too far for 2 steps
    board = _board_with_unit("u1", start)
    with pytest.raises(ValueError):
        move_unit(board, unit, dest, max_steps=2)


def test_move_unit_blocked_by_obstacle():
    unit = make_unit("u1")
    start = Coordinate(3, 3)
    # Place obstacles to block all paths to (3, 5)
    board = _board_with_unit("u1", start)
    # Block the direct path
    board.obstacles.add(Coordinate(3, 4))
    board.obstacles.add(Coordinate(2, 4))
    board.obstacles.add(Coordinate(4, 4))
    board.obstacles.add(Coordinate(2, 5))
    board.obstacles.add(Coordinate(4, 5))
    # (3,5) is now unreachable in 1 step from (3,3) since (3,4) is blocked
    # and diagonal paths are also blocked
    with pytest.raises(ValueError):
        move_unit(board, unit, Coordinate(3, 5), max_steps=1)


def test_move_unit_updates_position_and_flag():
    unit = make_unit("u1")
    start = Coordinate(1, 1)
    dest = Coordinate(2, 1)  # one step right (orthogonal)
    board = _board_with_unit("u1", start)
    move_unit(board, unit, dest, max_steps=1)
    assert board.unit_positions["u1"] == dest
    assert unit.has_moved is True


# ---------------------------------------------------------------------------
# can_attack
# ---------------------------------------------------------------------------

def test_can_attack_melee_adjacent():
    board = Board()
    a = Coordinate(3, 3)
    d = Coordinate(4, 4)  # diagonal adjacent = Chebyshev 1
    result = can_attack(a, d, board)
    assert result == (True, True)


def test_can_attack_melee_all_8_directions():
    board = Board()
    center = Coordinate(4, 4)
    for dc in [-1, 0, 1]:
        for dr in [-1, 0, 1]:
            if dc == 0 and dr == 0:
                continue
            neighbor = Coordinate(center.col + dc, center.row + dr)
            ok, is_melee = can_attack(center, neighbor, board)
            assert ok is True
            assert is_melee is True


def test_can_attack_ranged_with_los():
    board = Board()
    a = Coordinate(0, 0)
    d = Coordinate(3, 0)  # distance 3, clear LOS
    ok, is_melee = can_attack(a, d, board)
    assert ok is True
    assert is_melee is False


def test_can_attack_ranged_blocked_los():
    board = Board()
    a = Coordinate(0, 0)
    d = Coordinate(3, 0)
    board.obstacles.add(Coordinate(1, 0))  # blocks LOS
    ok, is_melee = can_attack(a, d, board)
    assert ok is False
    assert is_melee is False


def test_can_attack_out_of_range():
    board = Board()
    a = Coordinate(0, 0)
    d = Coordinate(5, 0)  # distance 5 > 3
    ok, is_melee = can_attack(a, d, board)
    assert ok is False
    assert is_melee is False


# ---------------------------------------------------------------------------
# resolve_attack
# ---------------------------------------------------------------------------

def _setup_combat(attacker_coord, defender_coord, seed=42):
    board = Board()
    attacker = make_unit("atk")
    defender = make_unit("def", team=2)
    board.unit_positions["atk"] = attacker_coord
    board.unit_positions["def"] = defender_coord
    roller = DiceRoller(seed=seed)
    return board, attacker, defender, roller


def test_resolve_attack_net_damage_seeded():
    board, attacker, defender, roller = _setup_combat(
        Coordinate(3, 3), Coordinate(4, 3)
    )
    result = resolve_attack(attacker, defender, board, roller)
    # net_damage must be >= 0
    assert result.net_damage >= 0
    assert result.attacker_id == "atk"
    assert result.defender_id == "def"
    assert result.is_melee is True


def test_resolve_attack_atk_boost_consumed():
    board, attacker, defender, roller = _setup_combat(
        Coordinate(3, 3), Coordinate(4, 3)
    )
    attacker.atk_boost_active = True
    result = resolve_attack(attacker, defender, board, roller)
    assert result.attack_bonus == 2
    assert attacker.atk_boost_active is False


def test_resolve_attack_def_boost_consumed():
    board, attacker, defender, roller = _setup_combat(
        Coordinate(3, 3), Coordinate(4, 3)
    )
    defender.def_boost_active = True
    result = resolve_attack(attacker, defender, board, roller)
    assert result.defense_bonus == 4
    assert defender.def_boost_active is False


def test_resolve_attack_net_damage_never_negative():
    # Run many seeds to ensure net_damage is always >= 0
    for seed in range(100):
        board, attacker, defender, roller = _setup_combat(
            Coordinate(3, 3), Coordinate(4, 3), seed=seed
        )
        defender.def_boost_active = True
        result = resolve_attack(attacker, defender, board, roller)
        assert result.net_damage >= 0


def test_resolve_attack_sets_has_acted():
    board, attacker, defender, roller = _setup_combat(
        Coordinate(3, 3), Coordinate(4, 3)
    )
    assert attacker.has_acted is False
    resolve_attack(attacker, defender, board, roller)
    assert attacker.has_acted is True


def test_resolve_attack_no_valid_attack_raises():
    board, attacker, defender, roller = _setup_combat(
        Coordinate(0, 0), Coordinate(7, 7)
    )
    with pytest.raises(ValueError):
        resolve_attack(attacker, defender, board, roller)


# ---------------------------------------------------------------------------
# reset_activation
# ---------------------------------------------------------------------------

def test_reset_activation():
    unit = make_unit()
    unit.has_moved = True
    unit.has_acted = True
    reset_activation(unit)
    assert unit.has_moved is False
    assert unit.has_acted is False
