"""
游戏配置管理器
管理游戏设置（音量、分辨率等）
配置持久化到 data/game_config.json
"""

import json
from pathlib import Path


class ConfigManager:
    """游戏配置管理器（单例）"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.config_path = Path(__file__).resolve().parent.parent / "data" / "game_config.json"
        self.config = self._load()

    def _load(self):
        """从文件加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"music_volume": 70}

    def save(self):
        """保存配置到文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def get_music_volume(self):
        """获取音乐音量 (0-100)"""
        return self.config.get("music_volume", 70)

    def set_music_volume(self, volume):
        """设置音乐音量 (0-100)"""
        volume = max(0, min(100, int(volume)))
        self.config["music_volume"] = volume
        # 立即应用到 pygame.mixer
        import pygame
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(volume / 100.0)
            try:
                from .audio_manager import get_audio_manager

                get_audio_manager().set_volume(volume / 100.0)
            except Exception:
                pass
        self.save()


# 全局配置管理器实例
config_manager = ConfigManager()
