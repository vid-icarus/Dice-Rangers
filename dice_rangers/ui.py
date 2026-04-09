"""UI state management and event handling framework for Dice Rangers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from dice_rangers.board import Coordinate
from dice_rangers.constants import COLUMNS, GRID_ORIGIN_X, GRID_ORIGIN_Y, TILE_SIZE
from dice_rangers.game import GameState, Phase

# Pygame event type constants (matching pygame values, no pygame import needed)
MOUSEBUTTONDOWN = 1025
KEYDOWN = 768
KEY_RETURN = 13
KEY_SPACE = 32

# ---------------------------------------------------------------------------
# CustomizerState import (lazy to avoid circular)
# ---------------------------------------------------------------------------

from dice_rangers.customizer import CustomizerState  # noqa: E402

# ---------------------------------------------------------------------------
# UIState
# ---------------------------------------------------------------------------

@dataclass
class UIState:
    # Current screen
    screen: str  # "title", "customize", "obstacles", "spawn", "gameplay", "victory"

    # Highlight sets
    highlights_move: set[Coordinate]
    highlights_attack: set[Coordinate]
    highlights_select: set[Coordinate]
    highlights_drop: set[Coordinate]

    # Banner / message display
    banner_text: str
    banner_sub: str
    banner_timer: float  # Seconds remaining; 0 = permanent

    # Dice result display
    dice_label: str
    dice_value: int | None
    dice_text: str
    dice_timer: float  # Seconds remaining; 0 = hidden

    # Buttons (list of dicts for testability)
    buttons: list[dict]

    # Customizer state
    customizer: CustomizerState | None

    # Obstacle placement
    obstacle_valid_squares: set[Coordinate]

    # Spawn placement
    spawn_valid_squares: set[Coordinate]

    # Gameplay state
    selected_action: str | None

    # Input locking
    input_locked: bool
    lock_timer: float  # Seconds remaining; 0 = unlocked


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def new_ui_state() -> UIState:
    """Create a fresh UIState with screen='title' and all defaults."""
    return UIState(
        screen="title",
        highlights_move=set(),
        highlights_attack=set(),
        highlights_select=set(),
        highlights_drop=set(),
        banner_text="",
        banner_sub="",
        banner_timer=0.0,
        dice_label="",
        dice_value=None,
        dice_text="",
        dice_timer=0.0,
        buttons=[],
        customizer=None,
        obstacle_valid_squares=set(),
        spawn_valid_squares=set(),
        selected_action=None,
        input_locked=False,
        lock_timer=0.0,
    )


# ---------------------------------------------------------------------------
# UIState → dict converter (for renderer)
# ---------------------------------------------------------------------------

def ui_state_to_dict(ui: UIState) -> dict:
    """Convert UIState to the ui_state dict that renderer.draw_frame() expects."""
    import pygame

    from dice_rangers.renderer import Button

    buttons = []
    for btn_dict in ui.buttons:
        bx, by, bw, bh = btn_dict["rect"]
        rect = pygame.Rect(bx, by, bw, bh)
        buttons.append(Button(
            rect=rect,
            label=btn_dict.get("label", ""),
            enabled=btn_dict.get("enabled", True),
            hovered=btn_dict.get("hovered", False),
            bg_color=btn_dict.get("bg_color", None),
            value=btn_dict.get("value", ""),
        ))

    return {
        "highlights_move": ui.highlights_move,
        "highlights_attack": ui.highlights_attack,
        "highlights_select": ui.highlights_select,
        "highlights_drop": ui.highlights_drop,
        "banner_text": ui.banner_text,
        "banner_sub": ui.banner_sub,
        "dice_label": ui.dice_label,
        "dice_value": ui.dice_value,
        "dice_text": ui.dice_text,
        "buttons": buttons,
    }


# ---------------------------------------------------------------------------
# Button hit test
# ---------------------------------------------------------------------------

def button_at(ui: UIState, pos: tuple[int, int]) -> dict | None:
    """Return the first enabled button dict that contains pos, or None."""
    px, py = pos
    for btn in ui.buttons:
        if not btn.get("enabled", True):
            continue
        bx, by, bw, bh = btn["rect"]
        if bx <= px < bx + bw and by <= py < by + bh:
            return btn
    return None


# ---------------------------------------------------------------------------
# Timer update
# ---------------------------------------------------------------------------

def update_timers(ui: UIState, dt: float) -> None:
    """Decrement positive timers; clear associated state when they expire."""
    if ui.banner_timer > 0:
        ui.banner_timer -= dt
        if ui.banner_timer <= 0:
            ui.banner_timer = 0.0
            ui.banner_text = ""
            ui.banner_sub = ""

    if ui.dice_timer > 0:
        ui.dice_timer -= dt
        if ui.dice_timer <= 0:
            ui.dice_timer = 0.0
            ui.dice_value = None
            ui.dice_text = ""
            ui.dice_label = ""

    if ui.lock_timer > 0:
        ui.lock_timer -= dt
        if ui.lock_timer <= 0:
            ui.lock_timer = 0.0
            ui.input_locked = False


# ---------------------------------------------------------------------------
# Master event handler
# ---------------------------------------------------------------------------

def handle_event(
    event_type: int,
    event_pos: tuple[int, int] | None,
    event_key: int | None,
    state: GameState,
    ui: UIState,
) -> None:
    """Route events to the appropriate screen handler."""
    if ui.input_locked:
        return

    if ui.screen == "title":
        handle_title_event(event_type, event_pos, event_key, state, ui)
    elif ui.screen == "customize":
        from dice_rangers.customizer import handle_customize_event
        handle_customize_event(event_type, event_pos, event_key, state, ui)
    elif ui.screen == "obstacles":
        handle_obstacle_event(event_type, event_pos, event_key, state, ui)
    elif ui.screen == "spawn":
        handle_spawn_event(event_type, event_pos, event_key, state, ui)
    # "gameplay" and "victory" handled in Part 2


# ---------------------------------------------------------------------------
# Title screen
# ---------------------------------------------------------------------------

def enter_title(ui: UIState) -> None:
    """Set up the title screen."""
    ui.screen = "title"
    ui.buttons = [{
        "rect": (300, 450, 200, 50),
        "label": "Start Game",
        "enabled": True,
        "value": "start_game",
        "bg_color": None,
        "hovered": False,
    }]
    ui.banner_text = "DICE RANGERS"
    ui.banner_sub = "Click Start to Play!"
    ui.banner_timer = 0.0  # permanent


def handle_title_event(
    event_type: int,
    event_pos: tuple[int, int] | None,
    event_key: int | None,
    state: GameState,
    ui: UIState,
) -> None:
    """Handle events on the title screen."""
    from dice_rangers.customizer import enter_customize

    if event_type == MOUSEBUTTONDOWN and event_pos is not None:
        btn = button_at(ui, event_pos)
        if btn is not None and btn.get("value") == "start_game":
            enter_customize(state, ui, team=1, unit_index=0)

    elif event_type == KEYDOWN and event_key in (KEY_RETURN, KEY_SPACE):
        enter_customize(state, ui, team=1, unit_index=0)


# ---------------------------------------------------------------------------
# Obstacle placement screen
# ---------------------------------------------------------------------------

def enter_obstacles(state: GameState, ui: UIState) -> None:
    """Set up the obstacle placement screen."""
    ui.screen = "obstacles"
    ui.banner_text = "Obstacle Placement"
    ui.banner_sub = f"Player {state.current_placer}'s Turn"
    ui.banner_timer = 0.0  # permanent
    ui.buttons = [{
        "rect": (300, 720, 200, 50),
        "label": "Roll Dice",
        "enabled": True,
        "value": "roll_dice",
        "bg_color": None,
        "hovered": False,
    }]
    ui.highlights_move = set()
    ui.highlights_attack = set()
    ui.highlights_select = set()
    ui.highlights_drop = set()
    ui.obstacle_valid_squares = set()
    ui.dice_value = None
    ui.dice_text = ""
    ui.dice_label = ""
    ui.dice_timer = 0.0


def handle_obstacle_event(
    event_type: int,
    event_pos: tuple[int, int] | None,
    event_key: int | None,
    state: GameState,
    ui: UIState,
) -> None:
    """Handle events on the obstacle placement screen."""
    from dice_rangers.game import place_obstacle, roll_obstacle

    if event_type != MOUSEBUTTONDOWN or event_pos is None:
        return

    btn = button_at(ui, event_pos)

    if btn is not None and btn.get("value") == "roll_dice":
        if state.obstacle_roll is None:
            col_roll, row_roll = roll_obstacle(state)
            rolled_coord = Coordinate(col_roll - 1, row_roll - 1)

            # Compute valid placement squares
            candidates = [rolled_coord] + state.board.get_adjacent_squares(rolled_coord)
            valid = set()
            for c in candidates:
                if not state.board.is_edge_square(c) and state.board.is_empty(c):
                    valid.add(c)
            ui.obstacle_valid_squares = valid
            ui.highlights_move = set(valid)

            # Show dice result
            ui.dice_label = "Obstacle Roll"
            ui.dice_value = col_roll
            ui.dice_text = f"{COLUMNS[col_roll - 1]}{row_roll}"
            ui.dice_timer = 0.0  # permanent

            # Update banner and remove Roll Dice button
            ui.banner_sub = "Click a highlighted square"
            ui.buttons = []  # Remove Roll Dice button
    else:
        # Grid click — check if obstacle_roll is pending
        if state.obstacle_roll is not None:
            coord = _pixel_to_grid(event_pos[0], event_pos[1])
            if coord is not None and coord in ui.obstacle_valid_squares:
                place_obstacle(state, coord)

                # Clear highlights and dice
                ui.highlights_move = set()
                ui.obstacle_valid_squares = set()
                ui.dice_value = None
                ui.dice_text = ""
                ui.dice_label = ""
                ui.dice_timer = 0.0

                if state.phase == Phase.OBSTACLE_PLACEMENT:
                    ui.banner_sub = f"Player {state.current_placer}'s Turn"
                    ui.buttons = [{
                        "rect": (300, 720, 200, 50),
                        "label": "Roll Dice",
                        "enabled": True,
                        "value": "roll_dice",
                        "bg_color": None,
                        "hovered": False,
                    }]
                elif state.phase == Phase.SPAWN_PLACEMENT:
                    enter_spawn(state, ui)


# ---------------------------------------------------------------------------
# Spawn placement screen
# ---------------------------------------------------------------------------

def enter_spawn(state: GameState, ui: UIState) -> None:
    """Set up the spawn placement screen."""
    ui.screen = "spawn"

    # Compute valid spawn squares for current spawner
    spawner = state.current_spawner
    valid = set()
    for row in range(8):
        for col in range(8):
            coord = Coordinate(col=col, row=row)
            if spawner == 1 and coord.row in {0, 1, 2}:
                if state.board.is_passable(coord):
                    valid.add(coord)
            elif spawner == 2 and coord.row in {5, 6, 7}:
                if state.board.is_passable(coord):
                    valid.add(coord)

    ui.spawn_valid_squares = valid
    ui.highlights_move = set(valid)
    ui.banner_text = "Spawn Placement"
    ui.banner_sub = (
        f"Player {state.current_spawner} — "
        f"Place Unit {state.units_spawned_this_player + 1}"
    )
    ui.banner_timer = 0.0  # permanent
    ui.buttons = []


def get_next_unplaced_unit(state: GameState) -> str:
    """Return the unit_id of the first unplaced unit for the current spawner."""
    spawner = state.current_spawner
    if spawner == 1:
        candidates = ["p1_unit1", "p1_unit2"]
    else:
        candidates = ["p2_unit1", "p2_unit2"]

    for unit_id in candidates:
        if unit_id not in state.board.unit_positions:
            return unit_id

    raise ValueError(f"No unplaced units found for spawner {spawner}")


def handle_spawn_event(
    event_type: int,
    event_pos: tuple[int, int] | None,
    event_key: int | None,
    state: GameState,
    ui: UIState,
) -> None:
    """Handle events on the spawn placement screen."""
    from dice_rangers.game import place_unit_on_board

    if event_type != MOUSEBUTTONDOWN or event_pos is None:
        return

    coord = _pixel_to_grid(event_pos[0], event_pos[1])
    if coord is None or coord not in ui.spawn_valid_squares:
        return

    unit_id = get_next_unplaced_unit(state)
    place_unit_on_board(state, unit_id, coord)

    if state.phase == Phase.SPAWN_PLACEMENT:
        # Recalculate valid spawn squares (exclude newly occupied)
        spawner = state.current_spawner
        valid = set()
        for row in range(8):
            for col in range(8):
                c = Coordinate(col=col, row=row)
                if spawner == 1 and c.row in {0, 1, 2}:
                    if state.board.is_passable(c):
                        valid.add(c)
                elif spawner == 2 and c.row in {5, 6, 7}:
                    if state.board.is_passable(c):
                        valid.add(c)
        ui.spawn_valid_squares = valid
        ui.highlights_move = set(valid)
        ui.banner_sub = (
            f"Player {state.current_spawner} — "
            f"Place Unit {state.units_spawned_this_player + 1}"
        )
    elif state.phase == Phase.ROUND_START:
        ui.screen = "gameplay"
        ui.highlights_move = set()
        ui.spawn_valid_squares = set()
        ui.banner_text = "Battle Begins!"
        ui.banner_sub = ""
        ui.banner_timer = 2.0


# ---------------------------------------------------------------------------
# Internal helper: pixel to grid (math-only, no pygame import)
# ---------------------------------------------------------------------------

def _pixel_to_grid(px: int, py: int) -> Coordinate | None:
    """Convert pixel position to board Coordinate, or None if outside grid."""
    col_f = px - GRID_ORIGIN_X
    row_f = py - GRID_ORIGIN_Y
    if col_f < 0 or row_f < 0:
        return None
    col = col_f // TILE_SIZE
    row = row_f // TILE_SIZE
    from dice_rangers.constants import GRID_SIZE
    if 0 <= col < GRID_SIZE and 0 <= row < GRID_SIZE:
        return Coordinate(col=col, row=row)
    return None
