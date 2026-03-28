# Dice Rangers

A grid-based hot-seat arena battling game built in Python. Players take turns on a shared screen, commanding their rangers in tactical grid combat where dice rolls determine the outcomes of attacks, abilities, and movement.

## Tech Stack

- **Language**: Python 3.12+
- **Packaging**: pyproject.toml (setuptools)
- **Testing**: pytest >= 7.0
- **Linting**: Ruff >= 0.4.0
- **Container**: Docker (python:3.12-slim)

## Project Structure

```
dice_rangers/          # Main game package
  __init__.py
  __main__.py          # Entry point (python -m dice_rangers)
  game.py              # Core game module
tests/                 # Test suite
  __init__.py
  test_game.py
pyproject.toml         # Package config & dependencies
Makefile               # Build/test/lint/run targets
.maestro/
  Dockerfile           # Dev container
  MAESTRO.md           # Agent prompt and project context
```

## Installation

```bash
pip install -e '.[dev]'
```

## Usage

```bash
python -m dice_rangers
```

## Development Commands

| Command      | Description                          |
|--------------|--------------------------------------|
| `make build` | Install package with dev dependencies |
| `make test`  | Run tests                            |
| `make lint`  | Lint with Ruff                       |
| `make run`   | Launch the game                      |
| `make clean` | Remove build artifacts               |
