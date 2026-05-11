from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import pygame


class AudioManager:
    """Small background audio helper for music and one-shot effects."""

    def __init__(self):
        self._active: List[Tuple[pygame.mixer.Sound, pygame.mixer.Channel]] = []

    def play_asset(self, asset_manager, relative_path: str, loops: int = 0, volume: Optional[float] = None) -> bool:
        if not pygame.mixer.get_init():
            print(f"[audio] mixer is not initialized, skip: {relative_path}")
            return False

        audio_path = asset_manager.get_asset_path(relative_path)
        return self.play_path(audio_path, loops=loops, volume=volume)

    def play_path(self, audio_path: Path, loops: int = 0, volume: Optional[float] = None) -> bool:
        if not pygame.mixer.get_init():
            print(f"[audio] mixer is not initialized, skip: {audio_path}")
            return False
        if not audio_path.exists():
            print(f"[audio] file not found: {audio_path}")
            return False

        try:
            from .config_manager import config_manager

            sound = pygame.mixer.Sound(str(audio_path))
            channel = pygame.mixer.find_channel(force=True)
            if channel is None:
                print(f"[audio] no free channel: {audio_path.name}")
                return False

            resolved_volume = config_manager.get_music_volume() / 100.0 if volume is None else volume
            channel.set_volume(max(0.0, min(1.0, float(resolved_volume))))
            channel.play(sound, loops=loops)
            self._active.append((sound, channel))
            self.update()
            print(f"[audio] background play: {audio_path.name}")
            return True
        except Exception as exc:
            print(f"[audio] failed to play {audio_path.name}: {exc}")
            return False

    def update(self):
        self._active = [(sound, channel) for sound, channel in self._active if channel.get_busy()]

    def set_volume(self, volume: float):
        resolved_volume = max(0.0, min(1.0, float(volume)))
        for _, channel in self._active:
            channel.set_volume(resolved_volume)

    def stop_all(self):
        for _, channel in self._active:
            channel.stop()
        self._active.clear()


def get_audio_manager() -> AudioManager:
    if not hasattr(get_audio_manager, "_instance"):
        get_audio_manager._instance = AudioManager()
    return get_audio_manager._instance
