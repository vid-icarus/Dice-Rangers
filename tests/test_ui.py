"""Tests for ui.py — no Pygame import required."""

from __future__ import annotations

from dice_rangers.ui import (
    button_at,
    enter_title,
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
