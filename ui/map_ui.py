"""
地图UI模块
显示别墅地图
"""

import pygame
from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_PANEL, COLOR_CHAMPAGNE


class MapUI:
    """地图UI类"""

    def __init__(self, asset_manager):
        self.asset_manager = asset_manager
        self.visible = False
        self.map_surface = None
        self.map_rect = None
        self.close_button_rect = None
        self.is_loaded = False

    def load_map(self):
        """加载地图图片"""
        if self.is_loaded:
            return
        try:
            self.map_surface = self.asset_manager.load_image(
                "ui/别墅地图.png",
                fallback_size=(SCREEN_WIDTH, SCREEN_HEIGHT)
            )
            self.is_loaded = True
        except Exception as e:
            print(f"[地图] 加载失败: {e}")
            self.is_loaded = False

    def show(self):
        """显示地图"""
        self.load_map()
        self.visible = True

    def hide(self):
        """隐藏地图"""
        self.visible = False

    def toggle(self):
        """切换显示/隐藏"""
        if self.visible:
            self.hide()
        else:
            self.show()

    def handle_event(self, event):
        """处理事件"""
        if not self.visible:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN:
            # 检查关闭按钮
            if self.close_button_rect and self.close_button_rect.collidepoint(event.pos):
                self.hide()
                return True
            # 点击地图外部关闭
            if self.map_rect and not self.map_rect.collidepoint(event.pos):
                self.hide()
                return True
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.hide()
                return True

        return False

    def draw(self, screen):
        """绘制地图"""
        if not self.visible or not self.map_surface:
            return

        # 半透明黑色遮罩
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # 计算地图居中位置
        map_width, map_height = self.map_surface.get_size()
        map_x = (SCREEN_WIDTH - map_width) // 2
        map_y = (SCREEN_HEIGHT - map_height) // 2
        self.map_rect = pygame.Rect(map_x, map_y, map_width, map_height)

        # 绘制地图
        screen.blit(self.map_surface, (map_x, map_y))

        # 绘制关闭按钮
        btn_size = 50
        btn_x = map_x + map_width - btn_size - 20
        btn_y = map_y + 20
        self.close_button_rect = pygame.Rect(btn_x, btn_y, btn_size, btn_size)

        btn_surface = pygame.Surface((btn_size, btn_size), pygame.SRCALPHA)
        btn_surface.fill((*COLOR_PANEL, 220))
        pygame.draw.rect(btn_surface, (*COLOR_CHAMPAGNE, 255),
                         (0, 0, btn_size, btn_size), 2, 8)
        screen.blit(btn_surface, (btn_x, btn_y))

        # 绘制X文字
        font_close = pygame.font.Font(None, 36)
        close_text = font_close.render("X", True, COLOR_CHAMPAGNE)
        close_rect = close_text.get_rect(center=(btn_x + btn_size // 2, btn_y + btn_size // 2))
        screen.blit(close_text, close_rect)