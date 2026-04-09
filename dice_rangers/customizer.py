"""Character customization screen logic for Dice Rangers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dice_rangers.game import GameState
    from dice_rangers.ui import UIState

from dice_rangers.units import (
    VALID_COLORS,
    VALID_RACES,
    Customization,
)

# ---------------------------------------------------------------------------
# CustomizerState
# ---------------------------------------------------------------------------

CUSTOMIZER_STEPS = [
    "race",
    "variant",
    "outfit",
    "primary_color",
    "secondary_color",
    "attack_flavor",
]


@dataclass
class CustomizerState:
    team: int
    unit_index: int  # 0 or 1
    step: str
    selected_race: str | None
    selected_variant: str | None
    selected_outfit: str | None
    selected_primary: str | None
    selected_secondary: str | None
    selected_flavor: str | None


# ---------------------------------------------------------------------------
# Button layout helpers
# ---------------------------------------------------------------------------

def build_option_buttons(
    labels: list[str],
    values: list[str],
    cols: int = 3,
    start_y: int = 250,
) -> list[dict]:
    """Create a grid of option button dicts centered horizontally."""
    btn_w = 180
    btn_h = 40
    gap = 10
    total_cols = min(cols, len(labels))
    total_width = total_cols * btn_w + (total_cols - 1) * gap
    start_x = (800 - total_width) // 2

    buttons = []
    for i, (label, value) in enumerate(zip(labels, values)):
        col_idx = i % cols
        row_idx = i // cols
        x = start_x + col_idx * (btn_w + gap)
        y = start_y + row_idx * (btn_h + gap)
        buttons.append({
            "rect": (x, y, btn_w, btn_h),
            "label": label,
            "enabled": True,
            "value": value,
            "bg_color": None,
            "hovered": False,
        })
    return buttons


def build_color_buttons(start_y: int = 250) -> list[dict]:
    """Create 16 square color swatch button dicts in a 4x4 grid, centered."""
    btn_size = 40
    gap = 10
    cols = 4
    total_width = cols * btn_size + (cols - 1) * gap
    start_x = (800 - total_width) // 2

    color_items = list(VALID_COLORS.items())  # (color_id, hex_str)
    # Build friendly short names from color IDs
    name_map = {
        "color_red": "Red",
        "color_orange": "Orange",
        "color_yellow": "Yellow",
        "color_lime": "Lime",
        "color_green": "Green",
        "color_teal": "Teal",
        "color_cyan": "Cyan",
        "color_blue": "Blue",
        "color_indigo": "Indigo",
        "color_purple": "Purple",
        "color_pink": "Pink",
        "color_hotpink": "Hot Pink",
        "color_white": "White",
        "color_ltgray": "Lt Gray",
        "color_dkgray": "Dk Gray",
        "color_black": "Black",
    }

    buttons = []
    for i, (color_id, hex_str) in enumerate(color_items):
        col_idx = i % cols
        row_idx = i // cols
        x = start_x + col_idx * (btn_size + gap)
        y = start_y + row_idx * (btn_size + gap)
        rgb = _hex_to_rgb(hex_str)
        label = name_map.get(color_id, color_id)
        buttons.append({
            "rect": (x, y, btn_size, btn_size),
            "label": label,
            "enabled": True,
            "value": color_id,
            "bg_color": rgb,
            "hovered": False,
        })
    return buttons


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Convert a hex color string like '#FF0000' to an RGB tuple."""
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# ---------------------------------------------------------------------------
# Step data
# ---------------------------------------------------------------------------

def get_step_options(cstate: CustomizerState) -> tuple[list[str], list[str]]:
    """Return (labels, values) for the current customizer step."""
    step = cstate.step

    if step == "race":
        labels = ["Bird", "Cat", "Spider", "Dragon", "Dino", "Robot"]
        values = [
            "race_bird", "race_cat", "race_spider",
            "race_dragon", "race_dino", "race_robot",
        ]
        return labels, values

    elif step == "variant":
        race = cstate.selected_race or "race_bird"
        variants = VALID_RACES.get(race, [])
        labels = [v.replace("_", " ").title() for v in variants]
        values = variants
        return labels, values

    elif step == "outfit":
        outfit_data = [
            ("Warrior", "outfit_warrior"),
            ("Wizard", "outfit_wizard"),
            ("Rogue", "outfit_rogue"),
            ("Ranger", "outfit_ranger"),
            ("Cleric", "outfit_cleric"),
            ("Knight", "outfit_knight"),
        ]
        labels = [d[0] for d in outfit_data]
        values = [d[1] for d in outfit_data]
        return labels, values

    elif step in ("primary_color", "secondary_color"):
        # Handled by build_color_buttons; return empty for non-color path
        return [], []

    elif step == "attack_flavor":
        flavor_data = [
            ("Sword", "atk_sword"),
            ("Bow", "atk_bow"),
            ("Magic", "atk_magic"),
            ("Hugs", "atk_hugs"),
            ("Hearts", "atk_hearts"),
            ("Butterflies", "atk_butterflies"),
            ("Sparkle", "atk_sparkle"),
            ("Laser", "atk_laser"),
            ("Slime", "atk_slime"),
        ]
        labels = [d[0] for d in flavor_data]
        values = [d[1] for d in flavor_data]
        return labels, values

    return [], []


def _step_display_name(step: str) -> str:
    return {
        "race": "Race",
        "variant": "Variant",
        "outfit": "Outfit",
        "primary_color": "Primary Color",
        "secondary_color": "Secondary Color",
        "attack_flavor": "Attack Flavor",
    }.get(step, step.replace("_", " ").title())


def _build_buttons_for_step(cstate: CustomizerState) -> list[dict]:
    """Build option buttons for the current step."""
    if cstate.step in ("primary_color", "secondary_color"):
        return build_color_buttons(start_y=250)
    else:
        labels, values = get_step_options(cstate)
        return build_option_buttons(labels, values, cols=3, start_y=250)


def _nav_buttons(show_back: bool = True) -> list[dict]:
    """Build Next and Back navigation buttons."""
    buttons = []
    # Next button (right side)
    buttons.append({
        "rect": (560, 680, 160, 50),
        "label": "Next",
        "enabled": True,
        "value": "__next__",
        "bg_color": None,
        "hovered": False,
    })
    if show_back:
        buttons.append({
            "rect": (80, 680, 160, 50),
            "label": "Back",
            "enabled": True,
            "value": "__back__",
            "bg_color": None,
            "hovered": False,
        })
    return buttons


# ---------------------------------------------------------------------------
# Enter customize
# ---------------------------------------------------------------------------

def enter_customize(state: GameState, ui: UIState, team: int, unit_index: int) -> None:
    """Set up the customization screen for a given team/unit."""
    ui.screen = "customize"
    cstate = CustomizerState(
        team=team,
        unit_index=unit_index,
        step="race",
        selected_race=None,
        selected_variant=None,
        selected_outfit=None,
        selected_primary=None,
        selected_secondary=None,
        selected_flavor=None,
    )
    ui.customizer = cstate
    ui.buttons = _build_buttons_for_step(cstate)
    ui.banner_text = f"Player {team} — Unit {unit_index + 1} — Choose Race"
    ui.banner_sub = ""
    ui.banner_timer = 0


# ---------------------------------------------------------------------------
# Event handler
# ---------------------------------------------------------------------------

def handle_customize_event(
    event_type: int,
    event_pos: tuple[int, int] | None,
    event_key: int | None,
    state: GameState,
    ui: UIState,
) -> None:
    """Handle events on the customization screen."""
    from dice_rangers.ui import MOUSEBUTTONDOWN, button_at

    if event_type != MOUSEBUTTONDOWN or event_pos is None:
        return

    cstate = ui.customizer
    if cstate is None:
        return

    btn = button_at(ui, event_pos)
    if btn is None:
        return

    value = btn.get("value", "")

    if value == "__next__":
        _advance_step(state, ui, cstate)
    elif value == "__back__":
        _go_back_step(ui, cstate)
    else:
        # Option button — store selection
        _store_selection(cstate, value)
        # Show nav buttons (option buttons + nav)
        option_btns = _build_buttons_for_step(cstate)
        nav_btns = _nav_buttons(show_back=(cstate.step != "race"))
        ui.buttons = option_btns + nav_btns


def _store_selection(cstate: CustomizerState, value: str) -> None:
    """Store the selected value for the current step."""
    step = cstate.step
    if step == "race":
        cstate.selected_race = value
        # Reset variant when race changes
        cstate.selected_variant = None
    elif step == "variant":
        cstate.selected_variant = value
    elif step == "outfit":
        cstate.selected_outfit = value
    elif step == "primary_color":
        cstate.selected_primary = value
    elif step == "secondary_color":
        cstate.selected_secondary = value
    elif step == "attack_flavor":
        cstate.selected_flavor = value


def _advance_step(state: GameState, ui: UIState, cstate: CustomizerState) -> None:
    """Advance to the next customization step or submit if on last step."""
    from dice_rangers.game import submit_customization
    from dice_rangers.ui import enter_obstacles

    step_idx = CUSTOMIZER_STEPS.index(cstate.step)

    # Validate current selection exists before advancing
    if not _has_selection(cstate):
        return  # Don't advance without a selection

    if cstate.step == "attack_flavor":
        # Final step — submit and transition
        customization = Customization(
            race=cstate.selected_race,
            variant=cstate.selected_variant,
            outfit=cstate.selected_outfit,
            primary_color=cstate.selected_primary,
            secondary_color=cstate.selected_secondary,
            attack_flavor=cstate.selected_flavor,
        )
        unit_id = f"p{cstate.team}_unit{cstate.unit_index + 1}"
        submit_customization(state, unit_id, cstate.team, customization)

        # Transition logic
        if cstate.unit_index == 0:
            enter_customize(state, ui, team=cstate.team, unit_index=1)
        elif cstate.unit_index == 1 and cstate.team == 1:
            enter_customize(state, ui, team=2, unit_index=0)
        elif cstate.unit_index == 1 and cstate.team == 2:
            enter_obstacles(state, ui)
    else:
        # Move to next step
        next_step = CUSTOMIZER_STEPS[step_idx + 1]
        cstate.step = next_step
        option_btns = _build_buttons_for_step(cstate)
        nav_btns = _nav_buttons(show_back=True)
        ui.buttons = option_btns + nav_btns
        ui.banner_text = (
            f"Player {cstate.team} — Unit {cstate.unit_index + 1} — "
            f"Choose {_step_display_name(next_step)}"
        )
        ui.banner_sub = ""


def _go_back_step(ui: UIState, cstate: CustomizerState) -> None:
    """Go back to the previous customization step."""
    step_idx = CUSTOMIZER_STEPS.index(cstate.step)
    if step_idx == 0:
        return  # Already at first step

    prev_step = CUSTOMIZER_STEPS[step_idx - 1]
    # Clear current step's selection
    _clear_selection(cstate, cstate.step)
    cstate.step = prev_step
    option_btns = _build_buttons_for_step(cstate)
    # Show nav: back only if not on first step
    show_back = (prev_step != "race")
    nav_btns = _nav_buttons(show_back=show_back)
    # If there's already a selection for this step, show nav buttons
    if _has_selection(cstate):
        ui.buttons = option_btns + nav_btns
    else:
        ui.buttons = option_btns
    ui.banner_text = (
        f"Player {cstate.team} — Unit {cstate.unit_index + 1} — "
        f"Choose {_step_display_name(prev_step)}"
    )
    ui.banner_sub = ""


def _has_selection(cstate: CustomizerState) -> bool:
    """Return True if the current step has a selection."""
    step = cstate.step
    if step == "race":
        return cstate.selected_race is not None
    elif step == "variant":
        return cstate.selected_variant is not None
    elif step == "outfit":
        return cstate.selected_outfit is not None
    elif step == "primary_color":
        return cstate.selected_primary is not None
    elif step == "secondary_color":
        return cstate.selected_secondary is not None
    elif step == "attack_flavor":
        return cstate.selected_flavor is not None
    return False


def _clear_selection(cstate: CustomizerState, step: str) -> None:
    """Clear the selection for a given step."""
    if step == "race":
        cstate.selected_race = None
        cstate.selected_variant = None  # variant depends on race
    elif step == "variant":
        cstate.selected_variant = None
    elif step == "outfit":
        cstate.selected_outfit = None
    elif step == "primary_color":
        cstate.selected_primary = None
    elif step == "secondary_color":
        cstate.selected_secondary = None
    elif step == "attack_flavor":
        cstate.selected_flavor = None
