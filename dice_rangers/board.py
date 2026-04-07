"""Grid, obstacles, coordinates, and pathfinding for the game board."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from dice_rangers.constants import (
    COLUMNS,
    EDGE_COLS,
    EDGE_ROWS,
    GRID_SIZE,
    MAX_RANGED_DISTANCE,
)


@dataclass(frozen=True)
class Coordinate:
    """An (col, row) position on the board.

    col: 0-indexed column (0 = 'A', 7 = 'H')
    row: 0-indexed row   (0 = row 1, 7 = row 8)
    """

    col: int  # 0–7
    row: int  # 0–7

    @staticmethod
    def from_label(label: str) -> "Coordinate":
        """Convert a display label like 'A1' or 'H8' to a Coordinate.

        Args:
            label: Two-character string, e.g. 'B3'.

        Returns:
            Corresponding Coordinate.

        Raises:
            ValueError: If the label is not valid.
        """
        if len(label) != 2:
            raise ValueError(f"Invalid coordinate label: {label!r}")
        col_char = label[0].upper()
        row_char = label[1]
        if col_char not in COLUMNS:
            raise ValueError(f"Invalid column in label: {label!r}")
        if not row_char.isdigit() or not (1 <= int(row_char) <= GRID_SIZE):
            raise ValueError(f"Invalid row in label: {label!r}")
        return Coordinate(col=COLUMNS.index(col_char), row=int(row_char) - 1)

    def to_label(self) -> str:
        """Convert this Coordinate to a display label like 'A1'.

        Returns:
            Two-character string representation.
        """
        return f"{COLUMNS[self.col]}{self.row + 1}"

    def is_valid(self) -> bool:
        """Return True if this coordinate is within the board bounds."""
        return 0 <= self.col < GRID_SIZE and 0 <= self.row < GRID_SIZE


class Board:
    """The 8×8 game board.

    Tracks obstacles, unit positions, and item positions.

    Conventions:
    - get_reachable_squares does NOT include the start square in its result.
    - Obstacles cannot be placed on edge squares or occupied squares.
    - has_line_of_sight allows the target square to contain a unit (for attacks).
    """

    def __init__(self) -> None:
        self.obstacles: set[Coordinate] = set()
        # unit_id -> Coordinate
        self.unit_positions: dict[str, Coordinate] = {}
        # Coordinate -> item_id
        self.item_positions: dict[Coordinate, str] = {}

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def _occupied_coords(self) -> set[Coordinate]:
        """Return all coordinates that have an obstacle, unit, or item."""
        coords: set[Coordinate] = set()
        coords |= self.obstacles
        coords |= set(self.unit_positions.values())
        coords |= set(self.item_positions.keys())
        return coords

    def is_empty(self, coord: Coordinate) -> bool:
        """True if no obstacle, unit, or item occupies this square."""
        return (
            coord not in self.obstacles
            and coord not in self.unit_positions.values()
            and coord not in self.item_positions
        )

    def is_passable(self, coord: Coordinate) -> bool:
        """True if a unit can move through this square (no obstacle or unit).

        Items do not block movement.
        """
        return coord not in self.obstacles and coord not in self.unit_positions.values()

    def is_edge_square(self, coord: Coordinate) -> bool:
        """True if this square is on row 1, row 8, column A, or column H."""
        col_label = COLUMNS[coord.col]
        row_label = coord.row + 1  # 1-indexed
        return row_label in EDGE_ROWS or col_label in EDGE_COLS

    # ------------------------------------------------------------------
    # Obstacle placement
    # ------------------------------------------------------------------

    def place_obstacle(self, coord: Coordinate) -> bool:
        """Place an obstacle at coord.

        Args:
            coord: Target square.

        Returns:
            True if the obstacle was placed successfully.

        Raises:
            ValueError: If the square is an edge square or already occupied.
        """
        if self.is_edge_square(coord):
            raise ValueError(
                f"Cannot place obstacle on edge square {coord.to_label()}"
            )
        if not self.is_empty(coord):
            raise ValueError(
                f"Cannot place obstacle on occupied square {coord.to_label()}"
            )
        self.obstacles.add(coord)
        return True

    # ------------------------------------------------------------------
    # Adjacency
    # ------------------------------------------------------------------

    def get_adjacent_squares(self, coord: Coordinate) -> list[Coordinate]:
        """Return all valid board squares adjacent to coord (8-directional).

        Args:
            coord: Center square.

        Returns:
            List of Coordinates that are within board bounds.
        """
        neighbors = []
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == 0 and dr == 0:
                    continue
                neighbor = Coordinate(col=coord.col + dc, row=coord.row + dr)
                if neighbor.is_valid():
                    neighbors.append(neighbor)
        return neighbors

    # ------------------------------------------------------------------
    # Movement (BFS, orthogonal only)
    # ------------------------------------------------------------------

    def get_reachable_squares(
        self, start: Coordinate, max_steps: int
    ) -> set[Coordinate]:
        """BFS flood-fill from start, orthogonal movement only.

        Cannot pass through obstacles or units. The start square itself is
        NOT included in the returned set.

        Args:
            start: Starting coordinate.
            max_steps: Maximum number of orthogonal steps.

        Returns:
            Set of reachable Coordinates (excluding start).
        """
        reachable: set[Coordinate] = set()
        # queue entries: (coord, steps_used)
        queue: deque[tuple[Coordinate, int]] = deque()
        queue.append((start, 0))
        visited: set[Coordinate] = {start}

        orthogonal_dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]

        while queue:
            current, steps = queue.popleft()
            if steps >= max_steps:
                continue
            for dc, dr in orthogonal_dirs:
                neighbor = Coordinate(col=current.col + dc, row=current.row + dr)
                if not neighbor.is_valid():
                    continue
                if neighbor in visited:
                    continue
                if not self.is_passable(neighbor):
                    continue
                visited.add(neighbor)
                reachable.add(neighbor)
                queue.append((neighbor, steps + 1))

        return reachable

    # ------------------------------------------------------------------
    # Line of sight (for ranged attacks)
    # ------------------------------------------------------------------

    def has_line_of_sight(self, origin: Coordinate, target: Coordinate) -> bool:
        """Check if origin has line of sight to target for a ranged attack.

        Valid only for straight lines (horizontal, vertical, or diagonal).
        Distance must be <= MAX_RANGED_DISTANCE (Chebyshev).
        All intermediate squares must be free of obstacles and units.
        The target square may contain a unit (the attack target).

        Args:
            origin: Attacker's position.
            target: Target position.

        Returns:
            True if line of sight is clear and within range.
        """
        dx = target.col - origin.col
        dy = target.row - origin.row

        # Must be a straight line: horizontal, vertical, or diagonal
        if not (dx == 0 or dy == 0 or abs(dx) == abs(dy)):
            return False

        # Must be within Chebyshev range
        chebyshev = max(abs(dx), abs(dy))
        if chebyshev == 0 or chebyshev > MAX_RANGED_DISTANCE:
            return False

        # Step direction
        step_col = 0 if dx == 0 else (1 if dx > 0 else -1)
        step_row = 0 if dy == 0 else (1 if dy > 0 else -1)

        # Check all intermediate squares (not origin, not target)
        steps = chebyshev
        for i in range(1, steps):
            intermediate = Coordinate(
                col=origin.col + step_col * i,
                row=origin.row + step_row * i,
            )
            # Intermediate squares must have no obstacle and no unit
            if intermediate in self.obstacles:
                return False
            if intermediate in self.unit_positions.values():
                return False

        return True
