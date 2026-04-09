"""Tests for ui.py — no Pygame import required."""

from __future__ import annotations

from dice_rangers.board import Coordinate
from dice_rangers.ui import (
    _clear_all_highlights,
    _item_name,
    button_at,
    enter_action_phase,
    enter_item_drop,
    enter_title,
    enter_unit_selection,
    enter_victory,
    handle_victory_event,
    new_ui_state,
    update_timers,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _btn(rect=(100, 100, 200, 50), label="Test", enabled=True, value="test"):
    return {
        "rect": rect,
        "label": label,
        "enabled": enabled,
        "value": value,
        "bg_color": None,
        "hovered": False,
    }


# ---------------------------------------------------------------------------
# new_ui_state
# ---------------------------------------------------------------------------

def test_new_ui_state_screen_is_title():
    ui = new_ui_state()
    assert ui.screen == "title"


def test_new_ui_state_highlights_empty():
    ui = new_ui_state()
    assert ui.highlights_move == set()
    assert ui.highlights_attack == set()
    assert ui.highlights_select == set()
    assert ui.highlights_drop == set()


def test_new_ui_state_timers_zero():
    ui = new_ui_state()
    assert ui.banner_timer == 0.0
    assert ui.dice_timer == 0.0
    assert ui.lock_timer == 0.0


def test_new_ui_state_not_locked():
    ui = new_ui_state()
    assert ui.input_locked is False


# ---------------------------------------------------------------------------
# button_at
# ---------------------------------------------------------------------------

def test_button_at_returns_button_when_inside():
    ui = new_ui_state()
    ui.buttons = [_btn()]
    result = button_at(ui, (150, 120))
    assert result is not None
    assert result["value"] == "test"


def test_button_at_returns_none_when_outside():
    ui = new_ui_state()
    ui.buttons = [_btn()]
    result = button_at(ui, (50, 50))
    assert result is None


def test_button_at_skips_disabled_buttons():
    ui = new_ui_state()
    ui.buttons = [_btn(enabled=False, value="disabled")]
    result = button_at(ui, (150, 120))
    assert result is None


def test_button_at_returns_first_match():
    ui = new_ui_state()
    ui.buttons = [
        _btn(value="first"),
        _btn(value="second"),
    ]
    result = button_at(ui, (150, 120))
    assert result["value"] == "first"


def test_button_at_boundary_inclusive_left():
    ui = new_ui_state()
    ui.buttons = [_btn(label="T", value="t")]
    assert button_at(ui, (100, 100)) is not None


def test_button_at_boundary_exclusive_right():
    ui = new_ui_state()
    ui.buttons = [_btn(label="T", value="t")]
    assert button_at(ui, (300, 100)) is None


# ---------------------------------------------------------------------------
# update_timers
# ---------------------------------------------------------------------------

def test_update_timers_decrements_banner_timer():
    ui = new_ui_state()
    ui.banner_text = "Hello"
    ui.banner_timer = 2.0
    update_timers(ui, 0.5)
    assert abs(ui.banner_timer - 1.5) < 1e-9
    assert ui.banner_text == "Hello"  # Not cleared yet


def test_update_timers_clears_banner_when_expires():
    ui = new_ui_state()
    ui.banner_text = "Hello"
    ui.banner_sub = "Sub"
    ui.banner_timer = 0.3
    update_timers(ui, 0.5)
    assert ui.banner_timer == 0.0
    assert ui.banner_text == ""
    assert ui.banner_sub == ""


def test_update_timers_permanent_banner_not_cleared():
    """banner_timer=0 means permanent — should never be auto-cleared."""
    ui = new_ui_state()
    ui.banner_text = "Permanent"
    ui.banner_timer = 0.0
    update_timers(ui, 1.0)
    assert ui.banner_text == "Permanent"
    assert ui.banner_timer == 0.0


def test_update_timers_decrements_dice_timer():
    ui = new_ui_state()
    ui.dice_value = 4
    ui.dice_timer = 1.0
    update_timers(ui, 0.3)
    assert abs(ui.dice_timer - 0.7) < 1e-9
    assert ui.dice_value == 4


def test_update_timers_clears_dice_when_expires():
    ui = new_ui_state()
    ui.dice_value = 4
    ui.dice_text = "D3"
    ui.dice_label = "Roll"
    ui.dice_timer = 0.1
    update_timers(ui, 0.5)
    assert ui.dice_value is None
    assert ui.dice_text == ""
    assert ui.dice_label == ""


def test_update_timers_unlocks_input_when_lock_expires():
    ui = new_ui_state()
    ui.input_locked = True
    ui.lock_timer = 0.2
    update_timers(ui, 0.5)
    assert ui.input_locked is False
    assert ui.lock_timer == 0.0


def test_update_timers_permanent_lock_timer_zero_not_unlocked():
    """lock_timer=0 with input_locked=True should stay locked (manual lock)."""
    ui = new_ui_state()
    ui.input_locked = True
    ui.lock_timer = 0.0
    update_timers(ui, 1.0)
    assert ui.input_locked is True


# ---------------------------------------------------------------------------
# enter_title
# ---------------------------------------------------------------------------

def test_enter_title_sets_screen():
    ui = new_ui_state()
    enter_title(ui)
    assert ui.screen == "title"


def test_enter_title_creates_start_button():
    ui = new_ui_state()
    enter_title(ui)
    assert len(ui.buttons) == 1
    btn = ui.buttons[0]
    assert btn["label"] == "Start Game"
    assert btn["enabled"] is True


def test_enter_title_sets_banner():
    ui = new_ui_state()
    enter_title(ui)
    assert ui.banner_text == "DICE RANGERS"
    assert ui.banner_sub == "Click Start to Play!"
    assert ui.banner_timer == 0.0  # permanent


# ---------------------------------------------------------------------------
# new_ui_state — new fields
# ---------------------------------------------------------------------------

def test_new_ui_state_restart_requested_false():
    ui = new_ui_state()
    assert ui.restart_requested is False


def test_new_ui_state_quit_requested_false():
    ui = new_ui_state()
    assert ui.quit_requested is False


# ---------------------------------------------------------------------------
# _clear_all_highlights
# ---------------------------------------------------------------------------

def test_clear_all_highlights_clears_all_sets():
    ui = new_ui_state()
    c = Coordinate(col=1, row=1)
    ui.highlights_move = {c}
    ui.highlights_attack = {c}
    ui.highlights_select = {c}
    ui.highlights_drop = {c}
    _clear_all_highlights(ui)
    assert ui.highlights_move == set()
    assert ui.highlights_attack == set()
    assert ui.highlights_select == set()
    assert ui.highlights_drop == set()


# ---------------------------------------------------------------------------
# _item_name
# ---------------------------------------------------------------------------

def test_item_name_heal():
    assert _item_name("item_heal") == "Healing Potion"


def test_item_name_atk():
    assert _item_name("item_atk") == "Attack Boost"


def test_item_name_def():
    assert _item_name("item_def") == "Defense Boost"


def test_item_name_unknown_fallback():
    assert _item_name("unknown") == "unknown"


# ---------------------------------------------------------------------------
# enter_victory
# ---------------------------------------------------------------------------

def _make_victory_state():
    """Create a minimal GameState-like object for victory tests."""
    from dice_rangers.game import new_game
    state = new_game(seed=42)
    # Manually set winner and phase for testing
    from dice_rangers.game import Phase
    state.phase = Phase.VICTORY
    state.winner = 1
    return state


def test_enter_victory_sets_screen():
    state = _make_victory_state()
    ui = new_ui_state()
    enter_victory(state, ui)
    assert ui.screen == "victory"


def test_enter_victory_banner_shows_winner():
    state = _make_victory_state()
    ui = new_ui_state()
    enter_victory(state, ui)
    assert "1" in ui.banner_text
    assert ui.banner_sub == "Congratulations!"


def test_enter_victory_creates_two_buttons():
    state = _make_victory_state()
    ui = new_ui_state()
    enter_victory(state, ui)
    assert len(ui.buttons) == 2
    values = {btn["value"] for btn in ui.buttons}
    assert "play_again" in values
    assert "quit" in values


def test_enter_victory_clears_highlights():
    state = _make_victory_state()
    ui = new_ui_state()
    c = Coordinate(col=2, row=2)
    ui.highlights_move = {c}
    ui.highlights_attack = {c}
    enter_victory(state, ui)
    assert ui.highlights_move == set()
    assert ui.highlights_attack == set()


# ---------------------------------------------------------------------------
# handle_victory_event
# ---------------------------------------------------------------------------

def _make_victory_ui():
    from dice_rangers.game import Phase, new_game
    state = new_game(seed=42)
    state.phase = Phase.VICTORY
    state.winner = 2
    ui = new_ui_state()
    enter_victory(state, ui)
    return state, ui


def test_handle_victory_play_again_sets_restart():
    state, ui = _make_victory_ui()
    # Find play_again button rect
    btn = next(b for b in ui.buttons if b["value"] == "play_again")
    bx, by, bw, bh = btn["rect"]
    click_pos = (bx + bw // 2, by + bh // 2)
    handle_victory_event(1025, click_pos, None, state, ui)
    assert ui.restart_requested is True
    assert ui.quit_requested is False


def test_handle_victory_quit_sets_quit():
    state, ui = _make_victory_ui()
    btn = next(b for b in ui.buttons if b["value"] == "quit")
    bx, by, bw, bh = btn["rect"]
    click_pos = (bx + bw // 2, by + bh // 2)
    handle_victory_event(1025, click_pos, None, state, ui)
    assert ui.quit_requested is True
    assert ui.restart_requested is False


# ---------------------------------------------------------------------------
# enter_unit_selection
# ---------------------------------------------------------------------------

def _make_activation_state():
    """Create a state ready for unit selection (ACTIVATION phase, no active unit)."""
    from dice_rangers.board import Coordinate
    from dice_rangers.game import (
        Phase,
        new_game,
        place_obstacle,
        place_unit_on_board,
        resolve_round_start,
        roll_obstacle,
        submit_customization,
    )
    from dice_rangers.units import Customization

    state = new_game(seed=1)
    # Customize both teams using valid field values
    c = Customization(
        race="race_bird", variant="eagle", outfit="outfit_warrior",
        primary_color="color_red", secondary_color="color_blue",
        attack_flavor="atk_sword",
    )
    submit_customization(state, "p1_unit1", 1, c)
    submit_customization(state, "p1_unit2", 1, c)
    submit_customization(state, "p2_unit1", 2, c)
    submit_customization(state, "p2_unit2", 2, c)

    # Place 8 obstacles (4 per player × 2 players)
    for _ in range(8):
        roll_obstacle(state)
        col_roll, row_roll = state.obstacle_roll
        rolled_coord = Coordinate(col=col_roll - 1, row=row_roll - 1)
        candidates = [rolled_coord] + state.board.get_adjacent_squares(rolled_coord)
        placed = False
        for candidate in candidates:
            try:
                place_obstacle(state, candidate)
                placed = True
                break
            except ValueError:
                continue
        if not placed:
            state.obstacle_roll = None
            state.obstacles_placed += 1
            state.current_placer = 2 if state.current_placer == 1 else 1
            if state.obstacles_placed == 8:
                state.phase = Phase.SPAWN_PLACEMENT
                state.current_spawner = 1
                state.units_spawned_this_player = 0

    # Place all 4 units
    place_unit_on_board(state, state.team1_units[0].unit_id, Coordinate(col=2, row=0))
    place_unit_on_board(state, state.team1_units[1].unit_id, Coordinate(col=3, row=0))
    place_unit_on_board(state, state.team2_units[0].unit_id, Coordinate(col=2, row=7))
    place_unit_on_board(state, state.team2_units[1].unit_id, Coordinate(col=3, row=7))

    # Resolve round start to get to ACTIVATION phase
    resolve_round_start(state)
    return state


def test_enter_unit_selection_banner_team1():
    state = _make_activation_state()
    ui = new_ui_state()
    state.activation_index = 0  # team 1's turn
    enter_unit_selection(state, ui)
    assert "Player 1" in ui.banner_text


def test_enter_unit_selection_banner_team2():
    state = _make_activation_state()
    ui = new_ui_state()
    state.activation_index = 1  # team 2's turn
    enter_unit_selection(state, ui)
    assert "Player 2" in ui.banner_text


def test_enter_unit_selection_highlights_choosable_positions():
    state = _make_activation_state()
    ui = new_ui_state()
    enter_unit_selection(state, ui)
    # Should have highlights for choosable units
    assert len(ui.highlights_select) > 0
    # All highlights should be actual unit positions
    all_positions = set(state.board.unit_positions.values())
    assert ui.highlights_select.issubset(all_positions)


# ---------------------------------------------------------------------------
# enter_action_phase
# ---------------------------------------------------------------------------

def _make_active_unit_state():
    """Create a state with an active unit."""
    from dice_rangers.game import begin_activation
    state = _make_activation_state()
    # Activate p1_unit1
    begin_activation(state, "p1_unit1")
    return state


def test_enter_action_phase_creates_five_buttons():
    state = _make_active_unit_state()
    ui = new_ui_state()
    enter_action_phase(state, ui)
    assert len(ui.buttons) == 5


def test_enter_action_phase_button_values():
    state = _make_active_unit_state()
    ui = new_ui_state()
    enter_action_phase(state, ui)
    values = [btn["value"] for btn in ui.buttons]
    assert "move" in values
    assert "attack" in values
    assert "use_item" in values
    assert "skip" in values
    assert "end_turn" in values


def test_enter_action_phase_end_turn_always_enabled():
    state = _make_active_unit_state()
    ui = new_ui_state()
    enter_action_phase(state, ui)
    end_turn_btn = next(b for b in ui.buttons if b["value"] == "end_turn")
    assert end_turn_btn["enabled"] is True


def test_enter_action_phase_clears_move_attack_drop_highlights():
    state = _make_active_unit_state()
    ui = new_ui_state()
    c = Coordinate(col=3, row=3)
    ui.highlights_move = {c}
    ui.highlights_attack = {c}
    ui.highlights_drop = {c}
    enter_action_phase(state, ui)
    assert ui.highlights_move == set()
    assert ui.highlights_attack == set()
    assert ui.highlights_drop == set()


def test_enter_action_phase_sets_select_highlight_to_active_unit():
    state = _make_active_unit_state()
    ui = new_ui_state()
    enter_action_phase(state, ui)
    active_pos = state.board.unit_positions.get(state.active_unit_id)
    assert active_pos in ui.highlights_select


# ---------------------------------------------------------------------------
# enter_item_drop
# ---------------------------------------------------------------------------

def test_enter_item_drop_clears_all_highlights_then_sets_drop():
    from dice_rangers.game import Phase
    state = _make_active_unit_state()
    ui = new_ui_state()
    c = Coordinate(col=2, row=2)
    ui.highlights_move = {c}
    ui.highlights_attack = {c}
    ui.highlights_select = {c}
    # Force ITEM_DROP phase and give unit an item
    state.phase = Phase.ITEM_DROP
    # Give the active unit an item so drop squares exist
    active_unit = next(
        u for u in state.team1_units + state.team2_units
        if u.unit_id == state.active_unit_id
    )
    active_unit.carrying_item = "item_heal"
    enter_item_drop(state, ui)
    # move/attack/select should be cleared
    assert ui.highlights_move == set()
    assert ui.highlights_attack == set()
    assert ui.highlights_select == set()
    # drop highlights should be set (may be empty if no valid squares,
    # but set is cleared then filled)
    assert isinstance(ui.highlights_drop, set)
    assert ui.banner_text == "Drop Item"
