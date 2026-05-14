"""
资源管理器模块
负责加载和管理游戏中的图片、字体等资源
"""

import os
import pygame
import json
import copy
from pathlib import Path

# 资源基础路径
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
DATA_DIR = BASE_DIR / "data"


class AssetManager:
    """资源管理器单例类"""

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

        # 缓存字典
        self.image_cache = {}
        self.font_cache = {}
        self.json_cache = {}

        # 字体路径
        self.font_path = ASSETS_DIR / "fonts" / "NotoSansSC-Regular.otf"
        self.font_available = self.font_path.exists()

        if not self.font_available:
            print(f"[警告] 中文字体未找到: {self.font_path}")
            print("[提示] 将使用系统字体 fallback")

    def load_image(self, path, fallback_size=None, fallback_color=None):
        """
        加载图片资源，失败时返回占位图
        :param path: 图片相对路径（相对于 assets 目录）
        :param fallback_size: 占位图尺寸 (width, height)
        :param fallback_color: 占位图颜色 RGB
        :return: pygame.Surface
        """
        # 构建绝对路径
        if not os.path.isabs(path):
            full_path = ASSETS_DIR / path
        else:
            full_path = Path(path)

        # 检查缓存
        cache_key = str(full_path)
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]

        # 尝试加载图片
        surface = None
        try:
            surface = pygame.image.load(str(full_path))
            surface = surface.convert_alpha() if surface.get_alpha() else surface.convert()
        except Exception as e:
            print(f"[错误] 无法加载图片 {full_path}: {e}")

        # 如果加载失败，创建占位图
        if surface is None:
            surface = self._create_placeholder(
                fallback_size or (400, 300),
                fallback_color or (50, 55, 65)
            )

        # 缩放到目标尺寸
        target_size = fallback_size
        if target_size:
            surface = pygame.transform.smoothscale(surface, target_size)

        # 缓存并返回
        self.image_cache[cache_key] = surface
        return surface

    def _create_placeholder(self, size, color):
        """创建占位图"""
        width, height = size
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        surface.fill(color)
        return surface

    def load_font(self, size):
        """
        加载字体
        :param size: 字体大小
        :return: pygame.Font
        """
        # 检查缓存
        if size in self.font_cache:
            return self.font_cache[size]

        font = None

        # 优先使用自定义字体
        if self.font_available:
            try:
                font = pygame.font.Font(str(self.font_path), size)
            except Exception as e:
                print(f"[错误] 无法加载自定义字体: {e}")
                self.font_available = False

        # 使用系统字体作为fallback
        if font is None:
            # 尝试多个可能的中文系统字体
            font_names = ["Microsoft YaHei", "SimHei", "PingFang SC", "Arial"]
            for font_name in font_names:
                try:
                    font = pygame.font.SysFont(font_name, size)
                    break
                except Exception:
                    continue

            # 如果还是没有，使用默认字体
            if font is None:
                font = pygame.font.Font(None, size)

        self.font_cache[size] = font
        return font

    def _load_json(self, filename, error_msg="数据"):
        """通用 JSON 加载方法"""
        if filename in self.json_cache:
            return copy.deepcopy(self.json_cache[filename])

        file_path = DATA_DIR / filename
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.json_cache[filename] = copy.deepcopy(data)
                return data
        except Exception as e:
            print(f"[错误] 无法加载{error_msg}: {e}")
        return {}

    def load_dialogues(self):
        """加载对话数据"""
        return self._load_json("dialogues.json", "对话数据")

    def load_scenes(self):
        """加载场景数据"""
        return self._load_json("scenes.json", "场景数据")

    def load_tasks(self):
        """加载任务数据"""
        return self._load_json("tasks.json", "任务数据")

    def load_cutscenes(self):
        """加载过场动画数据"""
        return self._load_json("cutscenes.json", "过场动画数据")

    def load_events(self):
        """加载事件数据"""
        return self._load_json("events.json", "事件数据")

    def clear_cache(self):
        """清空缓存"""
        self.image_cache.clear()
        self.font_cache.clear()
        self.json_cache.clear()

    def get_asset_path(self, relative_path: str) -> Path:
        """
        获取资源文件的绝对路径
        :param relative_path: 相对于 assets 目录的路径
        :return: Path对象
        """
        if os.path.isabs(relative_path):
            return Path(relative_path)
        return ASSETS_DIR / relative_path

    @property
    def asset_base_path(self) -> Path:
        """获取资源基础路径"""
        return ASSETS_DIR
