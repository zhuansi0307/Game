"""
设置场景
游戏设置界面
"""

import pygame
from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG_DARK, COLOR_TEXT, COLOR_CHAMPAGNE, COLOR_PANEL
from engine.scene_manager import BaseScene
from engine.ui import draw_text, draw_menu_button, draw_panel, draw_slider
from engine.config_manager import config_manager


class SettingsScene(BaseScene):
    """设置场景"""

    def __init__(self, scene_manager, asset_manager):
        """
        初始化设置场景
        :param scene_manager: 场景管理器
        :param asset_manager: 资源管理器
        """
        super().__init__(scene_manager)
        self.asset_manager = asset_manager

        # 加载字体
        self.font_title = asset_manager.load_font(48)
        self.font_text = asset_manager.load_font(28)
        self.font_slider = asset_manager.load_font(24)

        # 鼠标位置
        self.mouse_pos = (0, 0)

        # 音量滑动条配置
        slider_width = 400
        slider_height = 30
        slider_x = SCREEN_WIDTH // 2 - slider_width // 2
        slider_y = SCREEN_HEIGHT // 2 + 20
        self.volume_slider_rect = pygame.Rect(slider_x, slider_y, slider_width, slider_height)

        # 滑动条拖动状态
        self.is_dragging_slider = False

        # 加载保存的音量值
        self.volume = config_manager.get_music_volume()

        # 返回按钮
        button_width = 200
        button_height = 50
        self.back_button = pygame.Rect(
            SCREEN_WIDTH // 2 - button_width // 2,
            SCREEN_HEIGHT // 2 + 120,
            button_width,
            button_height
        )

        # 淡入效果
        self.fade_in = 0.0

        print("[设置场景] 初始化完成")

    def on_enter(self, **kwargs):
        """进入场景时调用"""
        self.fade_in = 0.0
        # 每次进入时刷新音量值
        self.volume = config_manager.get_music_volume()
        print("[设置场景] 进入设置场景")

    def handle_event(self, event):
        """处理事件"""
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            if self.is_dragging_slider:
                # 计算新值
                ratio = (event.pos[0] - self.volume_slider_rect.left) / self.volume_slider_rect.width
                ratio = max(0.0, min(1.0, ratio))
                self.volume = int(ratio * 100)
                config_manager.set_music_volume(self.volume)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # 左键点击
                if self.volume_slider_rect.collidepoint(self.mouse_pos):
                    self.is_dragging_slider = True
                    # 点击滑动条直接跳到该位置
                    ratio = (event.pos[0] - self.volume_slider_rect.left) / self.volume_slider_rect.width
                    ratio = max(0.0, min(1.0, ratio))
                    self.volume = int(ratio * 100)
                    config_manager.set_music_volume(self.volume)
                elif self.back_button.collidepoint(self.mouse_pos):
                    self.scene_manager.change_scene("main_menu")

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.is_dragging_slider = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.scene_manager.change_scene("main_menu")

        return False

    def update(self, dt):
        """每帧更新"""
        if self.fade_in < 1.0:
            self.fade_in += dt * 2
            if self.fade_in > 1.0:
                self.fade_in = 1.0

    def draw(self, screen):
        """绘制场景"""
        # 绘制背景
        self._draw_background(screen)

        # 绘制标题
        self._draw_title(screen)

        # 绘制音量滑动条
        self._draw_volume_slider(screen)

        # 绘制返回按钮
        self._draw_back_button(screen)

        # 绘制淡入效果
        if self.fade_in < 1.0:
            fade_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            fade_surface.fill(COLOR_BG_DARK)
            fade_surface.set_alpha(int(255 * (1 - self.fade_in)))
            screen.blit(fade_surface, (0, 0))

    def _draw_background(self, screen):
        """绘制背景"""
        screen.fill(COLOR_BG_DARK)

        # 绘制半透明面板背景
        panel_rect = (SCREEN_WIDTH // 2 - 400, SCREEN_HEIGHT // 2 - 150, 800, 350)
        draw_panel(screen, panel_rect, alpha=200, border=True)

    def _draw_title(self, screen):
        """绘制标题"""
        title = "游戏设置"
        title_surface = self.font_title.render(title, True, COLOR_CHAMPAGNE)
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80))
        screen.blit(title_surface, title_rect)

    def _draw_volume_slider(self, screen):
        """绘制音量滑动条"""
        draw_slider(
            screen,
            self.volume_slider_rect,
            self.volume,
            font=self.font_slider,
            label="音量",
            min_value=0,
            max_value=100
        )

    def _draw_back_button(self, screen):
        """绘制返回按钮"""
        hovered = self.back_button.collidepoint(self.mouse_pos)
        draw_menu_button(screen, self.back_button, "返回主菜单", self.font_text, hovered)