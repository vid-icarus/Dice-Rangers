"""Sound effects & music management — placeholder for V1."""

from __future__ import annotations


class AudioManager:
    """Placeholder audio manager. All methods are no-ops for V1."""

    def __init__(self) -> None:
        self._initialized = False

    def init(self) -> None:
        """Initialize audio system. Safe to call even if SDL audio unavailable."""
        try:
            import pygame.mixer
            pygame.mixer.init()
            self._initialized = True
        except Exception:
            self._initialized = False

    def play_sfx(self, name: str) -> None:
        """Play a sound effect by name. No-op in V1."""

    def play_music(self, name: str) -> None:
        """Play background music by name. No-op in V1."""

    def stop_music(self) -> None:
        """Stop background music. No-op in V1."""
