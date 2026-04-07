"""Dice rolling mechanics with deterministic RNG support."""

import random


class DiceRoller:
    """Central dice roller. All game systems should use a shared instance."""

    def __init__(self, seed: int | None = None) -> None:
        """
        Create a DiceRoller.

        Args:
            seed: Optional integer seed for deterministic/repeatable results.
                  If None, uses system entropy (non-deterministic).
        """
        self._rng = random.Random(seed)

    def roll(self, sides: int) -> int:
        """Roll a single die with the given number of sides.

        Args:
            sides: Number of sides on the die (e.g. 4, 6, 8).

        Returns:
            An integer in the range [1, sides].
        """
        return self._rng.randint(1, sides)

    def roll_2d8(self) -> tuple[int, int]:
        """Roll two 8-sided dice (convenience method for coordinate rolls).

        Returns:
            A tuple of two integers, each in the range [1, 8].
        """
        return (self.roll(8), self.roll(8))
