"""Pygame application entry point for Dice Rangers."""

import sys

import pygame

from dice_rangers.constants import FPS
from dice_rangers.game import new_game
from dice_rangers.renderer import draw_frame, init_display


def run() -> None:
    """Launch the Dice Rangers Pygame application."""
    screen = init_display()
    clock = pygame.time.Clock()
    state = new_game()
    ui_state: dict = {}  # Populated by UI module in future hotfix

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        draw_frame(screen, state, ui_state)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()
