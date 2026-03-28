# Dice Rangers

## Overview
Dice Rangers is a grid-based hot-seat arena battling game built in Python with Pygame. Two players take turns on a shared screen, commanding their rangers in tactical grid combat where dice rolls determine the outcomes of attacks, abilities, and movement. Targeted at kids (ages 5+) with cute 16-bit pixel art, fun animations, and kid-friendly theming.

## Tech Stack
- **Language**: Python 3.12+
- **Game Framework**: Pygame
- **Packaging**: pyproject.toml (setuptools)
- **Testing**: pytest
- **Linting**: Ruff
- **Container**: Docker (python:3.12-slim)

## Project Structure
\`\`\`
dice_rangers/          # Main game package
  __init__.py
  __main__.py          # Entry point (python -m dice_rangers)
  game.py              # Core game loop & state management
  board.py             # Grid, obstacles, coordinates
  units.py             # Unit data, movement, combat
  dice.py              # Dice rolling mechanics
  items.py             # Item spawning, pickup, usage
  events.py            # Board events system
  customizer.py        # Character customization logic
  renderer.py          # Pygame rendering & animations
  ui.py                # HUD, menus, setup screens
  audio.py             # Sound effects & music management
  constants.py         # Game constants & configuration
assets/
  sprites/             # Pixel art character & tile sprites (placeholders for V1)
  audio/               # Sound effects & music files (placeholders for V1)
  fonts/               # Pixel fonts
tests/                 # Test suite
  __init__.py
  test_game.py
  test_board.py
  test_units.py
  test_dice.py
  test_items.py
  test_combat.py
pyproject.toml         # Package config & dependencies
Makefile               # Build/test/lint/run targets
.maestro/
  Dockerfile           # Dev container
  MAESTRO.md           # This file
\`\`\`

## Development Commands
- `make build` â Install package with dev dependencies
- `make test` â Run tests
- `make lint` â Lint with Ruff
- `make run` â Launch the game
- `make clean` â Remove build artifacts

## Key Design Decisions
- **Pygame** for desktop 2D rendering (not web-based)
- **Mouse-primary controls** with optional keyboard support (arrow keys + space/enter)
- **Placeholder art/audio for V1** â colored shapes, simple icons, basic sounds
- **Shared team HP** (20 morale per team, may revisit after playtesting)
- **Alternating unit activation** (P1âP2âP1âP2, can't activate same unit twice in a row)
- **Cosmetic-only customization** (race, outfit, colors, attack flavor have no gameplay effect)
- **Orthogonal movement, 8-direction attacks** with line-of-sight for ranged
- **Game logic separated from rendering** for testability
- **Deterministic RNG seeding** available for tests
