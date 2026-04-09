"""Pygame application entry point for Dice Rangers."""

import sys

import pygame

from dice_rangers.constants import FPS
from dice_rangers.game import Phase, new_game
from dice_rangers.renderer import draw_frame, init_display
from dice_rangers.ui import (
    enter_title,
    enter_unit_selection,
    enter_victory,
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

        # Check restart/quit flags
        if ui.quit_requested:
            break
        if ui.restart_requested:
            state = new_game()
            ui = new_ui_state()
            enter_title(ui)
            continue

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

        # Update timers (pure UI, no game state)
        update_timers(ui, dt)

        # Post-lock transitions (checked AFTER timers update)
        if not ui.input_locked and ui.screen == "gameplay":
            # After round-start banner lock expires → enter unit selection
            if (
                state.phase == Phase.ACTIVATION
                and state.active_unit_id is None
                and ui.selected_action is None
                and not ui.buttons
            ):
                enter_unit_selection(state, ui)
            # After attack-victory lock expires → enter victory
            if state.phase == Phase.VICTORY:
                enter_victory(state, ui)

        draw_frame(screen, state, ui_state_to_dict(ui))
        pygame.display.flip()

    pygame.quit()
    sys.exit()
