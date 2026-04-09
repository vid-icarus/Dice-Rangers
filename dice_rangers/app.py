"""Pygame application entry point for Dice Rangers."""

import sys

import pygame

from dice_rangers.constants import FPS
from dice_rangers.game import new_game
from dice_rangers.renderer import draw_frame, init_display
from dice_rangers.ui import (
    enter_title,
    handle_event,
    new_ui_state,
    ui_state_to_dict,
    update_timers,
)


def run() -> None:
    """Launch the Dice Rangers Pygame application."""
    screen = init_display()
    clock = pygame.time.Clock()
    state = new_game()
    ui = new_ui_state()
    enter_title(ui)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                # Decompose Pygame event into plain data for testable handler
                event_pos = getattr(event, "pos", None)
                event_key = getattr(event, "key", None)
                handle_event(event.type, event_pos, event_key, state, ui)

        # Update hover states for buttons
        mx, my = pygame.mouse.get_pos()
        for btn_dict in ui.buttons:
            bx, by, bw, bh = btn_dict["rect"]
            btn_dict["hovered"] = btn_dict.get("enabled", True) and (
                bx <= mx < bx + bw and by <= my < by + bh
            )

        update_timers(ui, dt)
        draw_frame(screen, state, ui_state_to_dict(ui))
        pygame.display.flip()

    pygame.quit()
    sys.exit()
