"""Tests for dice.py — DiceRoller mechanics."""

from dice_rangers.dice import DiceRoller


def test_seeded_roller_is_repeatable():
    """Same seed produces same sequence of rolls."""
    roller1 = DiceRoller(seed=42)
    roller2 = DiceRoller(seed=42)
    results1 = [roller1.roll(6) for _ in range(20)]
    results2 = [roller2.roll(6) for _ in range(20)]
    assert results1 == results2


def test_different_seeds_differ():
    """Different seeds (usually) produce different sequences."""
    roller1 = DiceRoller(seed=1)
    roller2 = DiceRoller(seed=2)
    results1 = [roller1.roll(6) for _ in range(20)]
    results2 = [roller2.roll(6) for _ in range(20)]
    assert results1 != results2


def test_roll_d6_range():
    """roll(6) always returns a value in [1, 6]."""
    roller = DiceRoller(seed=0)
    for _ in range(200):
        result = roller.roll(6)
        assert 1 <= result <= 6


def test_roll_d4_range():
    """roll(4) always returns a value in [1, 4]."""
    roller = DiceRoller(seed=0)
    for _ in range(200):
        result = roller.roll(4)
        assert 1 <= result <= 4


def test_roll_d8_range():
    """roll(8) always returns a value in [1, 8]."""
    roller = DiceRoller(seed=0)
    for _ in range(200):
        result = roller.roll(8)
        assert 1 <= result <= 8


def test_roll_2d8_returns_tuple():
    """roll_2d8() returns a tuple of two values."""
    roller = DiceRoller(seed=7)
    result = roller.roll_2d8()
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_roll_2d8_range():
    """roll_2d8() each value is in [1, 8]."""
    roller = DiceRoller(seed=7)
    for _ in range(200):
        a, b = roller.roll_2d8()
        assert 1 <= a <= 8
        assert 1 <= b <= 8


def test_unseeded_roller_works():
    """Unseeded roller produces valid results (no crash)."""
    roller = DiceRoller()
    for _ in range(10):
        assert 1 <= roller.roll(6) <= 6
