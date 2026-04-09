"""Tests for events.py — board event resolution."""


from dice_rangers.board import Board, Coordinate
from dice_rangers.constants import GRID_SIZE
from dice_rangers.events import resolve_board_event

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FixedRoller:
    """A roller that returns a fixed sequence of values."""

    def __init__(self, values):
        self._values = list(values)
        self._idx = 0

    def roll(self, sides):
        val = self._values[self._idx % len(self._values)]
        self._idx += 1
        return val

    def roll_2d8(self):
        col = self.roll(8)
        row = self.roll(8)
        return (col, row)


# ---------------------------------------------------------------------------
# "nothing" event (rolls 1 or 2)
# ---------------------------------------------------------------------------

def test_nothing_event_roll_1():
    board = Board()
    roller = FixedRoller([1])
    event = resolve_board_event(board, roller)
    assert event.event_roll == 1
    assert event.event_type == "nothing"
    assert event.spawn_coord is None
    assert event.item_id is None


def test_nothing_event_roll_2():
    board = Board()
    roller = FixedRoller([2])
    event = resolve_board_event(board, roller)
    assert event.event_roll == 2
    assert event.event_type == "nothing"
    assert event.spawn_coord is None


# ---------------------------------------------------------------------------
# Spawn heal (rolls 3 or 4)
# ---------------------------------------------------------------------------

def test_spawn_heal_roll_3():
    board = Board()
    # event roll=3, then coord rolls 1,1 -> Coordinate(0,0)
    roller = FixedRoller([3, 1, 1])
    event = resolve_board_event(board, roller)
    assert event.event_roll == 3
    assert event.event_type == "spawn_heal"
    assert event.item_id == "item_heal"
    assert event.spawn_coord == Coordinate(0, 0)
    assert board.item_positions[Coordinate(0, 0)] == "item_heal"


def test_spawn_heal_roll_4():
    board = Board()
    roller = FixedRoller([4, 2, 3])
    event = resolve_board_event(board, roller)
    assert event.event_type == "spawn_heal"
    assert event.item_id == "item_heal"
    assert event.spawn_coord is not None
    assert board.item_positions[event.spawn_coord] == "item_heal"


# ---------------------------------------------------------------------------
# Spawn atk (rolls 5 or 6)
# ---------------------------------------------------------------------------

def test_spawn_atk_roll_5():
    board = Board()
    roller = FixedRoller([5, 4, 4])
    event = resolve_board_event(board, roller)
    assert event.event_type == "spawn_atk"
    assert event.item_id == "item_atk"
    assert event.spawn_coord is not None
    assert board.item_positions[event.spawn_coord] == "item_atk"


def test_spawn_atk_roll_6():
    board = Board()
    roller = FixedRoller([6, 5, 5])
    event = resolve_board_event(board, roller)
    assert event.event_type == "spawn_atk"
    assert event.item_id == "item_atk"


# ---------------------------------------------------------------------------
# Spawn def (rolls 7 or 8)
# ---------------------------------------------------------------------------

def test_spawn_def_roll_7():
    board = Board()
    roller = FixedRoller([7, 6, 6])
    event = resolve_board_event(board, roller)
    assert event.event_type == "spawn_def"
    assert event.item_id == "item_def"
    assert event.spawn_coord is not None
    assert board.item_positions[event.spawn_coord] == "item_def"


def test_spawn_def_roll_8():
    board = Board()
    roller = FixedRoller([8, 7, 7])
    event = resolve_board_event(board, roller)
    assert event.event_type == "spawn_def"
    assert event.item_id == "item_def"


# ---------------------------------------------------------------------------
# Item appears in board.item_positions at correct coordinate
# ---------------------------------------------------------------------------

def test_spawned_item_in_board_positions():
    board = Board()
    roller = FixedRoller([3, 3, 3])  # heal, coord (2,2) -> Coordinate(2,2)
    event = resolve_board_event(board, roller)
    assert event.spawn_coord in board.item_positions
    assert board.item_positions[event.spawn_coord] == event.item_id


# ---------------------------------------------------------------------------
# Re-roll when initial coordinate is occupied
# ---------------------------------------------------------------------------

def test_reroll_when_occupied():
    board = Board()
    # Block (0,0) with an obstacle — but obstacles can't go on edge squares,
    # so use a unit instead
    board.unit_positions["blocker"] = Coordinate(0, 0)
    # First coord roll hits (0,0) which is occupied, second hits (1,1) which is empty
    # event=3, col1=1,row1=1 -> (0,0) occupied, col2=2,row2=2 -> (1,1) empty
    roller = FixedRoller([3, 1, 1, 2, 2])
    event = resolve_board_event(board, roller)
    assert event.spawn_coord == Coordinate(1, 1)
    assert board.item_positions[Coordinate(1, 1)] == "item_heal"


# ---------------------------------------------------------------------------
# No spawn when board is completely full
# ---------------------------------------------------------------------------

def test_no_spawn_when_board_full():
    board = Board()
    # Fill every square with a unit
    uid = 0
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            board.unit_positions[f"u{uid}"] = Coordinate(c, r)
            uid += 1
    roller = FixedRoller([3, 1, 1])
    event = resolve_board_event(board, roller)
    assert event.event_type == "spawn_heal"
    assert event.spawn_coord is None
    assert event.item_id is None


# ---------------------------------------------------------------------------
# Spawn on empty board always succeeds on first roll
# ---------------------------------------------------------------------------

def test_spawn_empty_board_first_roll():
    board = Board()
    roller = FixedRoller([5, 4, 4])  # atk, coord (3,3)
    event = resolve_board_event(board, roller)
    assert event.spawn_coord == Coordinate(3, 3)
    assert board.item_positions[Coordinate(3, 3)] == "item_atk"
