"""Tests for customizer.py — no Pygame import required."""

from __future__ import annotations

from dice_rangers.customizer import (
    CUSTOMIZER_STEPS,
    CustomizerState,
    _hex_to_rgb,
    build_color_buttons,
    build_option_buttons,
    get_step_options,
)
from dice_rangers.units import VALID_COLORS, VALID_RACES

# ---------------------------------------------------------------------------
# build_option_buttons
# ---------------------------------------------------------------------------

def test_build_option_buttons_correct_count():
    labels = ["A", "B", "C", "D", "E", "F"]
    values = ["a", "b", "c", "d", "e", "f"]
    buttons = build_option_buttons(labels, values, cols=3)
    assert len(buttons) == 6


def test_build_option_buttons_two_rows_with_six_labels():
    labels = ["A", "B", "C", "D", "E", "F"]
    values = ["a", "b", "c", "d", "e", "f"]
    buttons = build_option_buttons(labels, values, cols=3)
    # First row: y = start_y, second row: y = start_y + btn_h + gap
    y_values = [btn["rect"][1] for btn in buttons]
    assert y_values[0] == y_values[1] == y_values[2]  # row 0
    assert y_values[3] == y_values[4] == y_values[5]  # row 1
    assert y_values[3] > y_values[0]


def test_build_option_buttons_button_structure():
    labels = ["Bird"]
    values = ["race_bird"]
    buttons = build_option_buttons(labels, values)
    btn = buttons[0]
    assert "rect" in btn
    assert "label" in btn
    assert "enabled" in btn
    assert "value" in btn
    assert "bg_color" in btn
    assert btn["label"] == "Bird"
    assert btn["value"] == "race_bird"
    assert btn["enabled"] is True
    assert btn["bg_color"] is None


def test_build_option_buttons_rect_is_tuple_of_four():
    buttons = build_option_buttons(["X"], ["x"])
    rect = buttons[0]["rect"]
    assert len(rect) == 4


# ---------------------------------------------------------------------------
# build_color_buttons
# ---------------------------------------------------------------------------

def test_build_color_buttons_creates_16():
    buttons = build_color_buttons()
    assert len(buttons) == 16


def test_build_color_buttons_have_bg_color():
    buttons = build_color_buttons()
    for btn in buttons:
        assert btn["bg_color"] is not None
        assert isinstance(btn["bg_color"], tuple)
        assert len(btn["bg_color"]) == 3


def test_build_color_buttons_rgb_matches_valid_colors():
    buttons = build_color_buttons()
    color_items = list(VALID_COLORS.items())
    for i, (color_id, hex_str) in enumerate(color_items):
        expected_rgb = _hex_to_rgb(hex_str)
        assert buttons[i]["bg_color"] == expected_rgb, (
            f"Color {color_id}: expected {expected_rgb}, got {buttons[i]['bg_color']}"
        )


def test_build_color_buttons_values_are_color_ids():
    buttons = build_color_buttons()
    color_ids = list(VALID_COLORS.keys())
    for i, btn in enumerate(buttons):
        assert btn["value"] == color_ids[i]


def test_build_color_buttons_all_enabled():
    buttons = build_color_buttons()
    for btn in buttons:
        assert btn["enabled"] is True


# ---------------------------------------------------------------------------
# get_step_options
# ---------------------------------------------------------------------------

def _make_cstate(step="race", race=None):
    return CustomizerState(
        team=1,
        unit_index=0,
        step=step,
        selected_race=race,
        selected_variant=None,
        selected_outfit=None,
        selected_primary=None,
        selected_secondary=None,
        selected_flavor=None,
    )


def test_get_step_options_race_returns_six():
    cstate = _make_cstate(step="race")
    labels, values = get_step_options(cstate)
    assert len(labels) == 6
    assert len(values) == 6


def test_get_step_options_race_labels():
    cstate = _make_cstate(step="race")
    labels, values = get_step_options(cstate)
    assert "Bird" in labels
    assert "Cat" in labels
    assert "Dragon" in labels


def test_get_step_options_race_values():
    cstate = _make_cstate(step="race")
    labels, values = get_step_options(cstate)
    assert "race_bird" in values
    assert "race_cat" in values
    assert "race_robot" in values


def test_get_step_options_variant_bird_returns_five():
    cstate = _make_cstate(step="variant", race="race_bird")
    labels, values = get_step_options(cstate)
    assert len(values) == len(VALID_RACES["race_bird"])
    assert len(values) == 5


def test_get_step_options_variant_values_match_valid_races():
    cstate = _make_cstate(step="variant", race="race_bird")
    labels, values = get_step_options(cstate)
    assert set(values) == set(VALID_RACES["race_bird"])


def test_get_step_options_outfit_returns_six():
    cstate = _make_cstate(step="outfit")
    labels, values = get_step_options(cstate)
    assert len(labels) == 6
    assert "outfit_warrior" in values
    assert "outfit_knight" in values


def test_get_step_options_attack_flavor_returns_nine():
    cstate = _make_cstate(step="attack_flavor")
    labels, values = get_step_options(cstate)
    assert len(labels) == 9
    assert "atk_sword" in values
    assert "atk_slime" in values


# ---------------------------------------------------------------------------
# CustomizerState step progression
# ---------------------------------------------------------------------------

def test_customizer_steps_order():
    assert CUSTOMIZER_STEPS[0] == "race"
    assert CUSTOMIZER_STEPS[1] == "variant"
    assert CUSTOMIZER_STEPS[2] == "outfit"
    assert CUSTOMIZER_STEPS[3] == "primary_color"
    assert CUSTOMIZER_STEPS[4] == "secondary_color"
    assert CUSTOMIZER_STEPS[5] == "attack_flavor"
    assert len(CUSTOMIZER_STEPS) == 6


def test_customizer_state_initial_all_none():
    cstate = CustomizerState(
        team=1,
        unit_index=0,
        step="race",
        selected_race=None,
        selected_variant=None,
        selected_outfit=None,
        selected_primary=None,
        selected_secondary=None,
        selected_flavor=None,
    )
    assert cstate.selected_race is None
    assert cstate.selected_variant is None
    assert cstate.selected_outfit is None
    assert cstate.selected_primary is None
    assert cstate.selected_secondary is None
    assert cstate.selected_flavor is None


# ---------------------------------------------------------------------------
# Unit ID generation (1-based)
# ---------------------------------------------------------------------------

def test_unit_id_team1_unit1():
    team = 1
    unit_index = 0
    unit_id = f"p{team}_unit{unit_index + 1}"
    assert unit_id == "p1_unit1"


def test_unit_id_team1_unit2():
    team = 1
    unit_index = 1
    unit_id = f"p{team}_unit{unit_index + 1}"
    assert unit_id == "p1_unit2"


def test_unit_id_team2_unit1():
    team = 2
    unit_index = 0
    unit_id = f"p{team}_unit{unit_index + 1}"
    assert unit_id == "p2_unit1"


def test_unit_id_team2_unit2():
    team = 2
    unit_index = 1
    unit_id = f"p{team}_unit{unit_index + 1}"
    assert unit_id == "p2_unit2"


# ---------------------------------------------------------------------------
# _hex_to_rgb helper
# ---------------------------------------------------------------------------

def test_hex_to_rgb_red():
    assert _hex_to_rgb("#FF0000") == (255, 0, 0)


def test_hex_to_rgb_white():
    assert _hex_to_rgb("#FFFFFF") == (255, 255, 255)


def test_hex_to_rgb_black():
    assert _hex_to_rgb("#000000") == (0, 0, 0)


def test_hex_to_rgb_mixed():
    assert _hex_to_rgb("#FF8800") == (255, 136, 0)
