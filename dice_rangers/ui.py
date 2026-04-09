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

    # App-level flags
    restart_requested: bool  # app.py checks and resets game
    quit_requested: bool     # app.py checks and exits


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
        restart_requested=False,
        quit_requested=False,
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
    elif ui.screen == "gameplay":
        handle_gameplay_event(event_type, event_pos, event_key, state, ui)
    elif ui.screen == "victory":
        handle_victory_event(event_type, event_pos, event_key, state, ui)


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
        enter_gameplay(state, ui)


# ---------------------------------------------------------------------------
# Item name helper
# ---------------------------------------------------------------------------

_ITEM_NAMES = {
    "item_heal": "Healing Potion",
    "item_atk": "Attack Boost",
    "item_def": "Defense Boost",
}


def _item_name(item_id: str) -> str:
    return _ITEM_NAMES.get(item_id, item_id)


# ---------------------------------------------------------------------------
# Highlight clearing
# ---------------------------------------------------------------------------

def _clear_all_highlights(ui: UIState) -> None:
    ui.highlights_move = set()
    ui.highlights_attack = set()
    ui.highlights_select = set()
    ui.highlights_drop = set()


# ---------------------------------------------------------------------------
# Gameplay entry points
# ---------------------------------------------------------------------------

def enter_gameplay(state: GameState, ui: UIState) -> None:
    """Transition to the gameplay screen and start the first round."""
    ui.screen = "gameplay"
    _clear_all_highlights(ui)
    ui.buttons = []
    enter_round_start(state, ui)


def enter_round_start(state: GameState, ui: UIState) -> None:
    """Resolve the round-start board event and show a banner."""
    from dice_rangers.game import resolve_round_start

    event = resolve_round_start(state)
    if event.event_type == "spawn_heal":
        banner_sub = "A Healing Potion appeared!"
    elif event.event_type == "spawn_atk":
        banner_sub = "An Attack Boost appeared!"
    elif event.event_type == "spawn_def":
        banner_sub = "A Defense Boost appeared!"
    else:
        banner_sub = "No board event"

    ui.banner_text = f"Round {state.round_number}"
    ui.banner_sub = banner_sub
    ui.banner_timer = 2.0
    ui.input_locked = True
    ui.lock_timer = 2.0
    ui.buttons = []


def enter_unit_selection(state: GameState, ui: UIState) -> None:
    """Set up the unit selection phase for the current team."""
    from dice_rangers.game import get_choosable_units

    team = 1 if state.activation_index % 2 == 0 else 2
    choosable = get_choosable_units(state)
    _clear_all_highlights(ui)
    for unit_id in choosable:
        pos = state.board.unit_positions.get(unit_id)
        if pos is not None:
            ui.highlights_select.add(pos)
    ui.banner_text = f"Player {team}'s Turn"
    ui.banner_sub = "Click a unit to activate"
    ui.banner_timer = 0  # permanent
    ui.buttons = []
    ui.selected_action = None


def enter_action_phase(state: GameState, ui: UIState) -> None:
    """Set up the action buttons for the currently active unit."""
    from dice_rangers.game import get_valid_actions

    actions = get_valid_actions(state)
    _clear_all_highlights(ui)

    # Highlight the active unit's position
    if state.active_unit_id is not None:
        pos = state.board.unit_positions.get(state.active_unit_id)
        if pos is not None:
            ui.highlights_select.add(pos)

    team = 1 if (state.activation_index - 1) % 2 == 0 else 2

    # Build action buttons in a horizontal row centred at y≈740
    button_defs = [
        ("Move", "move", actions.get("move", False)),
        ("Attack", "attack", actions.get("attack", False)),
        ("Use Item", "use_item", actions.get("use_item", False)),
        ("Skip", "skip", actions.get("skip", False)),
        ("End Turn", "end_turn", True),
    ]
    btn_w, btn_h, gap = 120, 40, 10
    total_w = len(button_defs) * btn_w + (len(button_defs) - 1) * gap
    start_x = (800 - total_w) // 2
    y = 740
    ui.buttons = []
    for i, (label, value, enabled) in enumerate(button_defs):
        x = start_x + i * (btn_w + gap)
        ui.buttons.append({
            "rect": (x, y, btn_w, btn_h),
            "label": label,
            "enabled": enabled,
            "value": value,
            "bg_color": None,
            "hovered": False,
        })

    ui.banner_text = f"Player {team}'s Turn"
    ui.banner_sub = f"Unit: {state.active_unit_id}"
    ui.banner_timer = 0
    ui.selected_action = None


def enter_item_drop(state: GameState, ui: UIState) -> None:
    """Set up the item drop phase."""
    from dice_rangers.game import get_drop_squares

    drop_squares = get_drop_squares(state)
    _clear_all_highlights(ui)
    for sq in drop_squares:
        ui.highlights_drop.add(sq)
    ui.banner_text = "Drop Item"
    ui.banner_sub = "Click a highlighted square to drop your old item"
    ui.banner_timer = 0
    ui.buttons = []


def enter_victory(state: GameState, ui: UIState) -> None:
    """Transition to the victory screen."""
    ui.screen = "victory"
    _clear_all_highlights(ui)
    ui.banner_text = f"Player {state.winner} Wins!"
    ui.banner_sub = "Congratulations!"
    ui.banner_timer = 0
    ui.buttons = [
        {
            "rect": (300, 500, 200, 50),
            "label": "Play Again",
            "enabled": True,
            "value": "play_again",
            "bg_color": None,
            "hovered": False,
        },
        {
            "rect": (300, 560, 200, 50),
            "label": "Quit",
            "enabled": True,
            "value": "quit",
            "bg_color": None,
            "hovered": False,
        },
    ]


# ---------------------------------------------------------------------------
# Gameplay event handler
# ---------------------------------------------------------------------------

def handle_gameplay_event(
    event_type: int,
    event_pos: tuple[int, int] | None,
    event_key: int | None,
    state: GameState,
    ui: UIState,
) -> None:
    """Handle events on the gameplay screen."""
    from dice_rangers.game import (
        Phase,
        begin_activation,
        do_attack,
        do_drop_item,
        do_move,
        do_skip_action,
        do_use_item,
        end_activation,
        get_attackable_targets,
        get_choosable_units,
        get_reachable_squares,
    )

    if ui.input_locked:
        return

    if event_type != MOUSEBUTTONDOWN or event_pos is None:
        return

    # ------------------------------------------------------------------
    # ITEM_DROP phase — short-circuit to drop handling first
    # ------------------------------------------------------------------
    if state.phase == Phase.ITEM_DROP:
        coord = _pixel_to_grid(event_pos[0], event_pos[1])
        if coord is not None and coord in ui.highlights_drop:
            do_drop_item(state, coord)
            enter_action_phase(state, ui)
        return

    # ------------------------------------------------------------------
    # No active unit → unit selection mode
    # ------------------------------------------------------------------
    if state.active_unit_id is None:
        coord = _pixel_to_grid(event_pos[0], event_pos[1])
        if coord is None:
            return
        choosable = get_choosable_units(state)
        # Find which choosable unit is at this coordinate
        chosen_id = None
        for unit_id in choosable:
            if state.board.unit_positions.get(unit_id) == coord:
                chosen_id = unit_id
                break
        if chosen_id is None:
            return
        roll = begin_activation(state, chosen_id)
        ui.dice_label = "Movement Roll"
        ui.dice_value = roll
        ui.dice_text = str(roll)
        ui.dice_timer = 3.0
        enter_action_phase(state, ui)
        return

    # ------------------------------------------------------------------
    # Active unit exists — check button clicks first
    # ------------------------------------------------------------------
    btn = button_at(ui, event_pos)
    if btn is not None and btn.get("enabled", True):
        value = btn.get("value")

        if value == "move":
            ui.selected_action = "move"
            reachable = get_reachable_squares(state)
            ui.highlights_attack = set()
            ui.highlights_move = reachable
            ui.banner_sub = "Click a square to move"

        elif value == "attack":
            ui.selected_action = "attack"
            targets = get_attackable_targets(state)
            ui.highlights_move = set()
            ui.highlights_attack = set()
            for tid in targets:
                pos = state.board.unit_positions.get(tid)
                if pos is not None:
                    ui.highlights_attack.add(pos)
            ui.banner_sub = "Click an enemy to attack"

        elif value == "use_item":
            result = do_use_item(state)
            if result.buff_activated is None:
                ui.banner_sub = f"Healed! Morale: {result.new_morale}"
            elif result.buff_activated == "atk_boost":
                ui.banner_sub = "Attack Boost activated!"
            elif result.buff_activated == "def_boost":
                ui.banner_sub = "Defense Boost activated!"
            ui.banner_timer = 1.5
            enter_action_phase(state, ui)

        elif value == "skip":
            do_skip_action(state)
            enter_action_phase(state, ui)

        elif value == "end_turn":
            end_activation(state)
            _clear_all_highlights(ui)
            ui.buttons = []
            ui.selected_action = None
            if state.phase == Phase.ROUND_START:
                enter_round_start(state, ui)
            elif state.phase == Phase.ACTIVATION:
                enter_unit_selection(state, ui)
            elif state.phase == Phase.VICTORY:
                enter_victory(state, ui)

        return

    # ------------------------------------------------------------------
    # Grid click with active unit
    # ------------------------------------------------------------------
    coord = _pixel_to_grid(event_pos[0], event_pos[1])
    if coord is None:
        return

    if ui.selected_action == "move":
        if coord in ui.highlights_move:
            result = do_move(state, coord)
            if result is not None:
                ui.banner_sub = f"Picked up {_item_name(result.picked_up)}!"
                ui.banner_timer = 1.5
                if state.phase == Phase.ITEM_DROP:
                    enter_item_drop(state, ui)
                    return
            enter_action_phase(state, ui)

    elif ui.selected_action == "attack":
        if coord in ui.highlights_attack:
            # Find the enemy unit at this coordinate
            target_id = None
            for uid, pos in state.board.unit_positions.items():
                if pos == coord:
                    target_id = uid
                    break
            if target_id is None:
                return
            result = do_attack(state, target_id)
            ui.dice_label = "Melee Attack" if result.is_melee else "Ranged Attack"
            ui.dice_value = result.attack_roll
            ui.dice_text = (
                f"Atk: {result.attack_roll}+{result.attack_bonus} vs "
                f"Def: {result.defense_roll}+{result.defense_bonus} = "
                f"{result.net_damage} dmg"
            )
            ui.dice_timer = 3.0
            ui.banner_sub = f"{result.net_damage} damage!"
            ui.banner_timer = 2.0
            if state.phase == Phase.VICTORY:
                ui.input_locked = True
                ui.lock_timer = 1.5
            else:
                enter_action_phase(state, ui)


# ---------------------------------------------------------------------------
# Victory event handler
# ---------------------------------------------------------------------------

def handle_victory_event(
    event_type: int,
    event_pos: tuple[int, int] | None,
    event_key: int | None,
    state: GameState,
    ui: UIState,
) -> None:
    """Handle events on the victory screen."""
    if event_type != MOUSEBUTTONDOWN or event_pos is None:
        return
    btn = button_at(ui, event_pos)
    if btn is None:
        return
    value = btn.get("value")
    if value == "play_again":
        ui.restart_requested = True
    elif value == "quit":
        ui.quit_requested = True


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
