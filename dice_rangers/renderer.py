"""Pygame rendering & animations for Dice Rangers."""

from __future__ import annotations

import os
from dataclasses import dataclass

import pygame
import pygame.freetype

from dice_rangers.board import Board, Coordinate
from dice_rangers.constants import (
    COLOR_BANNER_BG,
    COLOR_BG,
    COLOR_BUTTON,
    COLOR_BUTTON_DISABLED,
    COLOR_BUTTON_HOVER,
    COLOR_GRID_DARK,
    COLOR_GRID_LIGHT,
    COLOR_GRID_LINE,
    COLOR_HIGHLIGHT_ATTACK,
    COLOR_HIGHLIGHT_DROP,
    COLOR_HIGHLIGHT_MOVE,
    COLOR_HIGHLIGHT_SELECT,
    COLOR_ITEM_ATK,
    COLOR_ITEM_DEF,
    COLOR_ITEM_HEAL,
    COLOR_OBSTACLE,
    COLOR_P1,
    COLOR_P2,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    GRID_ORIGIN_X,
    GRID_ORIGIN_Y,
    GRID_SIZE,
    ITEM_RADIUS,
    OBSTACLE_PADDING,
    TILE_SIZE,
    UNIT_RADIUS,
    WINDOW_SIZE,
)
from dice_rangers.game import GameState
from dice_rangers.units import VALID_COLORS

# ---------------------------------------------------------------------------
# Font cache
# ---------------------------------------------------------------------------

_font_cache: dict[int, pygame.freetype.Font] = {}
_FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")


def get_font(size: int) -> pygame.freetype.Font:
    """Return a cached freetype font at the given size."""
    if size in _font_cache:
        return _font_cache[size]

    font = None

    # Try loading a .ttf from assets/fonts/
    if os.path.isdir(_FONT_DIR):
        for fname in os.listdir(_FONT_DIR):
            if fname.lower().endswith(".ttf"):
                try:
                    font = pygame.freetype.Font(os.path.join(_FONT_DIR, fname), size)
                    break
                except Exception:
                    font = None

    # Fallback: freetype default font (None = built-in default)
    if font is None:
        try:
            font = pygame.freetype.Font(None, size)
        except Exception:
            pass

    # Fallback: SysFont if available
    if font is None and hasattr(pygame.freetype, "SysFont"):
        try:
            font = pygame.freetype.SysFont("arial", size)
        except Exception:
            pass

    if font is None:
        raise RuntimeError(
            "Could not initialize any font. Ensure pygame is installed correctly "
            "and SDL_ttf or freetype libraries are available."
        )

    _font_cache[size] = font
    return font


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def init_display() -> pygame.Surface:
    """Initialize Pygame and return the display surface."""
    pygame.init()
    try:
        pygame.freetype.init()
    except Exception:
        pass  # freetype init failure handled gracefully in get_font
    screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
    pygame.display.set_caption("Dice Rangers")
    return screen


# ---------------------------------------------------------------------------
# Coordinate helpers
# ---------------------------------------------------------------------------


def grid_to_pixel(coord: Coordinate) -> tuple[int, int]:
    """Convert a board Coordinate to the pixel top-left corner of the tile."""
    return (
        GRID_ORIGIN_X + coord.col * TILE_SIZE,
        GRID_ORIGIN_Y + coord.row * TILE_SIZE,
    )


def pixel_to_grid(px: int, py: int) -> Coordinate | None:
    """Convert a pixel position to a board Coordinate, or None if outside grid."""
    col_f = px - GRID_ORIGIN_X
    row_f = py - GRID_ORIGIN_Y
    if col_f < 0 or row_f < 0:
        return None
    col = col_f // TILE_SIZE
    row = row_f // TILE_SIZE
    if 0 <= col < GRID_SIZE and 0 <= row < GRID_SIZE:
        return Coordinate(col=col, row=row)
    return None


# ---------------------------------------------------------------------------
# Grid drawing
# ---------------------------------------------------------------------------


def draw_grid(surface: pygame.Surface) -> None:
    """Draw the 8×8 checkerboard grid with coordinate labels."""
    font = get_font(14)
    columns = "ABCDEFGH"

    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            color = COLOR_GRID_LIGHT if (col + row) % 2 == 0 else COLOR_GRID_DARK
            rect = pygame.Rect(
                GRID_ORIGIN_X + col * TILE_SIZE,
                GRID_ORIGIN_Y + row * TILE_SIZE,
                TILE_SIZE,
                TILE_SIZE,
            )
            pygame.draw.rect(surface, color, rect)

    # Grid lines
    for i in range(GRID_SIZE + 1):
        # Vertical lines
        x = GRID_ORIGIN_X + i * TILE_SIZE
        pygame.draw.line(
            surface,
            COLOR_GRID_LINE,
            (x, GRID_ORIGIN_Y),
            (x, GRID_ORIGIN_Y + GRID_SIZE * TILE_SIZE),
            1,
        )
        # Horizontal lines
        y = GRID_ORIGIN_Y + i * TILE_SIZE
        pygame.draw.line(
            surface,
            COLOR_GRID_LINE,
            (GRID_ORIGIN_X, y),
            (GRID_ORIGIN_X + GRID_SIZE * TILE_SIZE, y),
            1,
        )

    # Column labels (A–H) along the top
    for col in range(GRID_SIZE):
        label = font.render(columns[col], fgcolor=COLOR_TEXT_DIM)[0]
        x = GRID_ORIGIN_X + col * TILE_SIZE + TILE_SIZE // 2 - label.get_width() // 2
        y = GRID_ORIGIN_Y - label.get_height() - 2
        surface.blit(label, (x, max(0, y)))

    # Row labels (1–8) along the left
    for row in range(GRID_SIZE):
        label = font.render(str(row + 1), fgcolor=COLOR_TEXT_DIM)[0]
        x = GRID_ORIGIN_X - label.get_width() - 2
        y = GRID_ORIGIN_Y + row * TILE_SIZE + TILE_SIZE // 2 - label.get_height() // 2
        surface.blit(label, (max(0, x), y))


# ---------------------------------------------------------------------------
# Obstacle drawing
# ---------------------------------------------------------------------------


def draw_obstacles(surface: pygame.Surface, board: Board) -> None:
    """Draw obstacles as dark inset rectangles with an X pattern."""
    lighter = (
        min(COLOR_OBSTACLE[0] + 30, 255),
        min(COLOR_OBSTACLE[1] + 30, 255),
        min(COLOR_OBSTACLE[2] + 30, 255),
    )
    for coord in board.obstacles:
        px, py = grid_to_pixel(coord)
        rect = pygame.Rect(
            px + OBSTACLE_PADDING,
            py + OBSTACLE_PADDING,
            TILE_SIZE - 2 * OBSTACLE_PADDING,
            TILE_SIZE - 2 * OBSTACLE_PADDING,
        )
        pygame.draw.rect(surface, COLOR_OBSTACLE, rect)
        # X pattern
        pygame.draw.line(surface, lighter, rect.topleft, rect.bottomright, 2)
        pygame.draw.line(surface, lighter, rect.topright, rect.bottomleft, 2)


# ---------------------------------------------------------------------------
# Item drawing
# ---------------------------------------------------------------------------

_ITEM_COLORS = {
    "item_heal": COLOR_ITEM_HEAL,
    "item_atk": COLOR_ITEM_ATK,
    "item_def": COLOR_ITEM_DEF,
}
_ITEM_SYMBOLS = {
    "item_heal": "+",
    "item_atk": "!",
    "item_def": "D",
}


def draw_items(surface: pygame.Surface, board: Board) -> None:
    """Draw items as colored circles with a symbol."""
    font = get_font(14)
    for coord, item_id in board.item_positions.items():
        px, py = grid_to_pixel(coord)
        cx = px + TILE_SIZE // 2
        cy = py + TILE_SIZE // 2
        color = _ITEM_COLORS.get(item_id, COLOR_ITEM_HEAL)
        pygame.draw.circle(surface, color, (cx, cy), ITEM_RADIUS)
        symbol = _ITEM_SYMBOLS.get(item_id, "?")
        text = font.render(symbol, fgcolor=COLOR_TEXT)[0]
        surface.blit(text, (cx - text.get_width() // 2, cy - text.get_height() // 2))


# ---------------------------------------------------------------------------
# Unit drawing
# ---------------------------------------------------------------------------

_RACE_LETTERS = {
    "bird": "B",
    "cat": "C",
    "spider": "S",
    "dragon": "D",
    "dino": "N",
    "robot": "R",
}


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """Convert a hex color string like '#FF0000' to an RGB tuple."""
    h = hex_str.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def draw_units(surface: pygame.Surface, state: GameState) -> None:
    """Draw all units on the board."""
    font = get_font(20)
    small_font = get_font(12)

    teams = [
        (state.team1_units, COLOR_P1, 1),
        (state.team2_units, COLOR_P2, 2),
    ]

    for units, team_color, _team_num in teams:
        for unit in units:
            coord = state.board.unit_positions.get(unit.unit_id)
            if coord is None:
                continue

            px, py = grid_to_pixel(coord)
            cx = px + TILE_SIZE // 2
            cy = py + TILE_SIZE // 2

            # Primary color from customization
            hex_color = VALID_COLORS.get(unit.customization.primary_color, "#888888")
            rgb = _hex_to_rgb(hex_color)

            # Draw filled circle (unit body)
            pygame.draw.circle(surface, rgb, (cx, cy), UNIT_RADIUS)
            # Draw team-colored border ring
            pygame.draw.circle(surface, team_color, (cx, cy), UNIT_RADIUS, 2)

            # Race letter in center
            letter = _RACE_LETTERS.get(unit.customization.race, "?")
            text = font.render(letter, fgcolor=COLOR_TEXT)[0]
            surface.blit(
                text, (cx - text.get_width() // 2, cy - text.get_height() // 2)
            )

            # Carrying item indicator — small dot bottom-right
            if unit.carrying_item is not None:
                dot_color = _ITEM_COLORS.get(unit.carrying_item, COLOR_ITEM_HEAL)
                dot_x = px + TILE_SIZE - 10
                dot_y = py + TILE_SIZE - 10
                pygame.draw.circle(surface, dot_color, (dot_x, dot_y), 6)

            # Boost indicators above unit
            indicator_x = cx
            indicator_y = cy - UNIT_RADIUS - 4
            if unit.atk_boost_active:
                atk_text = small_font.render("▲", fgcolor=(220, 60, 60))[0]
                surface.blit(
                    atk_text,
                    (
                        indicator_x - atk_text.get_width() // 2,
                        indicator_y - atk_text.get_height(),
                    ),
                )
                indicator_y -= atk_text.get_height()
            if unit.def_boost_active:
                def_text = small_font.render("■", fgcolor=(60, 100, 220))[0]
                surface.blit(
                    def_text,
                    (
                        indicator_x - def_text.get_width() // 2,
                        indicator_y - def_text.get_height(),
                    ),
                )


# ---------------------------------------------------------------------------
# Highlight drawing
# ---------------------------------------------------------------------------


def draw_highlights(
    surface: pygame.Surface,
    coords: set[Coordinate],
    color: tuple[int, int, int, int],
) -> None:
    """Draw semi-transparent highlight rectangles using a per-pixel-alpha surface."""
    if not coords:
        return
    alpha_surface = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
    for coord in coords:
        px, py = grid_to_pixel(coord)
        rect = pygame.Rect(px, py, TILE_SIZE, TILE_SIZE)
        pygame.draw.rect(alpha_surface, color, rect)
    surface.blit(alpha_surface, (0, 0))


# ---------------------------------------------------------------------------
# HUD drawing
# ---------------------------------------------------------------------------


def draw_hud(surface: pygame.Surface, state: GameState) -> None:
    """Draw morale counters and phase info as overlays."""
    morale_font = get_font(18)
    phase_font = get_font(16)

    # Helper to draw a semi-transparent background behind text
    def draw_overlay_text(
        text: str,
        font: pygame.freetype.Font,
        color: tuple[int, int, int],
        x: int,
        y: int,
        padding: int = 4,
    ) -> None:
        rendered = font.render(text, fgcolor=color)[0]
        bg = pygame.Surface(
            (rendered.get_width() + padding * 2, rendered.get_height() + padding * 2),
            pygame.SRCALPHA,
        )
        bg.fill((20, 20, 30, 180))
        surface.blit(bg, (x - padding, y - padding))
        surface.blit(rendered, (x, y))

    # P1 morale — top-left
    p1_text = f"P1: \u2665 {state.team1_morale}"
    draw_overlay_text(
        p1_text, morale_font, COLOR_P1, GRID_ORIGIN_X + 4, GRID_ORIGIN_Y + 4
    )

    # P2 morale — top-right
    p2_text = f"P2: \u2665 {state.team2_morale}"
    p2_rendered = morale_font.render(p2_text, fgcolor=COLOR_P2)[0]
    p2_x = GRID_ORIGIN_X + GRID_SIZE * TILE_SIZE - p2_rendered.get_width() - 4
    draw_overlay_text(p2_text, morale_font, COLOR_P2, p2_x, GRID_ORIGIN_Y + 4)

    # Phase/turn info — bottom-center
    phase_label = _phase_label(state)
    phase_rendered = phase_font.render(phase_label, fgcolor=COLOR_TEXT)[0]
    phase_x = WINDOW_SIZE // 2 - phase_rendered.get_width() // 2
    phase_y = GRID_ORIGIN_Y + GRID_SIZE * TILE_SIZE - phase_rendered.get_height() - 6
    draw_overlay_text(phase_label, phase_font, COLOR_TEXT, phase_x, phase_y)


def _phase_label(state: GameState) -> str:
    """Return a human-readable phase/turn label."""
    from dice_rangers.game import Phase

    phase_names = {
        Phase.P1_CUSTOMIZE: "Player 1: Customize",
        Phase.P2_CUSTOMIZE: "Player 2: Customize",
        Phase.OBSTACLE_PLACEMENT: "Obstacle Placement",
        Phase.SPAWN_PLACEMENT: "Spawn Placement",
        Phase.ROUND_START: f"Round {state.round_number} — Start",
        Phase.ACTIVATION: f"Player {state.active_player}'s Turn",
        Phase.ITEM_DROP: "Drop Item",
        Phase.VICTORY: f"Player {state.winner} Wins!",
    }
    return phase_names.get(state.phase, str(state.phase))


# ---------------------------------------------------------------------------
# Banner drawing
# ---------------------------------------------------------------------------


def draw_banner(surface: pygame.Surface, text: str, sub_text: str = "") -> None:
    """Draw a centered banner across the middle of the screen."""
    big_font = get_font(28)
    sub_font = get_font(18)

    big_rendered = big_font.render(text, fgcolor=COLOR_TEXT)[0]
    sub_rendered = (
        sub_font.render(sub_text, fgcolor=COLOR_TEXT)[0] if sub_text else None
    )

    sub_h = sub_rendered.get_height() + 4 if sub_rendered else 0
    total_h = big_rendered.get_height() + sub_h
    banner_w = WINDOW_SIZE
    banner_h = total_h + 24
    banner_y = WINDOW_SIZE // 2 - banner_h // 2

    alpha_surface = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
    alpha_surface.fill(COLOR_BANNER_BG)
    surface.blit(alpha_surface, (0, banner_y))

    # Main text
    bx = WINDOW_SIZE // 2 - big_rendered.get_width() // 2
    by = banner_y + 12
    surface.blit(big_rendered, (bx, by))

    # Sub text
    if sub_rendered:
        sx = WINDOW_SIZE // 2 - sub_rendered.get_width() // 2
        sy = by + big_rendered.get_height() + 4
        surface.blit(sub_rendered, (sx, sy))


# ---------------------------------------------------------------------------
# Button drawing
# ---------------------------------------------------------------------------


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    enabled: bool = True
    hovered: bool = False
    # Override background color (for color swatches)
    bg_color: tuple[int, int, int] | None = None
    # Stores the ID this button represents (e.g., "race_bird")
    value: str = ""


def draw_button(surface: pygame.Surface, button: Button) -> None:
    """Draw a single button with rounded corners."""
    if button.bg_color is not None:
        bg_color = button.bg_color
        text_color = COLOR_TEXT
    elif not button.enabled:
        bg_color = COLOR_BUTTON_DISABLED
        text_color = COLOR_TEXT_DIM
    elif button.hovered:
        bg_color = COLOR_BUTTON_HOVER
        text_color = COLOR_TEXT
    else:
        bg_color = COLOR_BUTTON
        text_color = COLOR_TEXT

    pygame.draw.rect(surface, bg_color, button.rect, border_radius=6)

    font = get_font(16)
    text = font.render(button.label, fgcolor=text_color)[0]
    tx = button.rect.centerx - text.get_width() // 2
    ty = button.rect.centery - text.get_height() // 2
    surface.blit(text, (tx, ty))


def draw_buttons(surface: pygame.Surface, buttons: list[Button]) -> None:
    """Draw all buttons in the list."""
    for button in buttons:
        draw_button(surface, button)


# ---------------------------------------------------------------------------
# Dice result drawing
# ---------------------------------------------------------------------------


def draw_dice_result(surface: pygame.Surface, label: str, value: int) -> None:
    """Draw a dice result overlay near the center-bottom of the screen."""
    label_font = get_font(16)
    value_font = get_font(32)

    label_rendered = label_font.render(label, fgcolor=COLOR_TEXT)[0]
    value_rendered = value_font.render(str(value), fgcolor=COLOR_TEXT)[0]

    padding = 12
    w = max(label_rendered.get_width(), value_rendered.get_width()) + padding * 2
    h = label_rendered.get_height() + value_rendered.get_height() + padding * 2 + 4
    x = WINDOW_SIZE // 2 - w // 2
    y = WINDOW_SIZE - h - 20

    alpha_surface = pygame.Surface((w, h), pygame.SRCALPHA)
    alpha_surface.fill((20, 20, 30, 200))
    surface.blit(alpha_surface, (x, y))
    pygame.draw.rect(
        surface, COLOR_TEXT_DIM, pygame.Rect(x, y, w, h), 1, border_radius=4
    )

    lx = x + w // 2 - label_rendered.get_width() // 2
    ly = y + padding
    surface.blit(label_rendered, (lx, ly))

    vx = x + w // 2 - value_rendered.get_width() // 2
    vy = ly + label_rendered.get_height() + 4
    surface.blit(value_rendered, (vx, vy))


# ---------------------------------------------------------------------------
# Master draw function
# ---------------------------------------------------------------------------


def draw_frame(surface: pygame.Surface, state: GameState, ui_state: dict) -> None:
    """Clear and redraw the entire frame."""
    surface.fill(COLOR_BG)

    # 1. Grid
    draw_grid(surface)

    # 2. Highlights
    move_coords: set[Coordinate] = ui_state.get("highlights_move", set())
    attack_coords: set[Coordinate] = ui_state.get("highlights_attack", set())
    select_coords: set[Coordinate] = ui_state.get("highlights_select", set())
    drop_coords: set[Coordinate] = ui_state.get("highlights_drop", set())

    draw_highlights(surface, move_coords, COLOR_HIGHLIGHT_MOVE)
    draw_highlights(surface, attack_coords, COLOR_HIGHLIGHT_ATTACK)
    draw_highlights(surface, select_coords, COLOR_HIGHLIGHT_SELECT)
    draw_highlights(surface, drop_coords, COLOR_HIGHLIGHT_DROP)

    # 3. Obstacles
    draw_obstacles(surface, state.board)

    # 4. Items
    draw_items(surface, state.board)

    # 5. Units
    draw_units(surface, state)

    # 6. HUD
    draw_hud(surface, state)

    # 7. Optional overlays
    banner_text: str = ui_state.get("banner_text", "")
    if banner_text:
        draw_banner(surface, banner_text, ui_state.get("banner_sub", ""))

    dice_label: str = ui_state.get("dice_label", "")
    if dice_label:
        draw_dice_result(surface, dice_label, ui_state.get("dice_value", 0))

    buttons: list[Button] = ui_state.get("buttons", [])
    if buttons:
        draw_buttons(surface, buttons)
