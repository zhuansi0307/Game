"""
热区UI组件
专门负责热区的视觉呈现（绘制光点、标签、详情卡片）
"""

import pygame
import math
from engine.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    COLOR_CHAMPAGNE, COLOR_CHAMPAGNE_BRIGHT, COLOR_TEXT, COLOR_PANEL, COLOR_PANEL_BORDER
)


COLOR_CHAMPAGNE_LIGHT = (248, 223, 155)
COLOR_DISCOVERED = (167, 243, 208)


class HotspotUI:
    """热区UI渲染器"""

    def __init__(self):
        self.base_radius = 8
        self.hover_radius = 15
        self.glow_radius = 44

    def draw(self, screen, hotspot, mouse_pos, fonts, time):
        """
        绘制热区UI
        :param screen: pygame屏幕surface
        :param hotspot: Hotspot逻辑对象
        :param mouse_pos: 鼠标位置
        :param fonts: 字体字典
        :param time: 游戏时间（用于呼吸动画）
        """
        if getattr(hotspot, 'destroyed', False):
            return

        render_type = getattr(hotspot, 'render_type', 'dot')

        if render_type == 'exclamation':
            self._draw_exclamation(screen, hotspot, mouse_pos, fonts, time)
        else:
            self._draw_dot_style(screen, hotspot, mouse_pos, fonts, time)

    def _draw_dot_style(self, screen, hotspot, mouse_pos, fonts, time):
        """原有的光点渲染方式"""
        progress = self._ease_out(hotspot.hover_progress)

        self._draw_dot(screen, hotspot, time, progress)
        
        if hotspot.hover_progress > 0.1:
            self._draw_label(screen, hotspot, fonts.get('small'), progress)
        
        if hotspot.hover_progress > 0.3:
            self._draw_card(screen, hotspot, fonts, progress)

    def _draw_exclamation(self, screen, hotspot, mouse_pos, fonts, time):
        """感叹号渲染方式"""
        breath = math.sin(time * 2.2) * 0.5 + 0.5
        progress = self._ease_out(hotspot.hover_progress)

        cx, cy = hotspot.dot_pos

        COLOR_EXCLAMATION = (255, 60, 60)
        COLOR_EXCLAMATION_GLOW = (255, 80, 80)

        glow_radius = int(60 + breath * 16)
        glow_alpha = int(120 + breath * 60)
        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        glow_center = (glow_radius, glow_radius)
        for r in range(glow_radius, 0, -3):
            falloff = 1 - r / glow_radius
            a = int(glow_alpha * falloff * falloff)
            pygame.draw.circle(glow_surface, (*COLOR_EXCLAMATION_GLOW, max(0, a)), glow_center, r)
        screen.blit(glow_surface, (cx - glow_radius, cy - glow_radius))

        exclamation_surface = pygame.Surface((120, 150), pygame.SRCALPHA)
        bar_width = 30
        bar_x = (120 - bar_width) // 2
        pygame.draw.rect(exclamation_surface, COLOR_EXCLAMATION, (bar_x, 0, bar_width, 96), border_radius=10)
        pygame.draw.circle(exclamation_surface, COLOR_EXCLAMATION, (60, 129), 18)
        screen.blit(exclamation_surface, (cx - 60, cy - 75))

        if hotspot.hover_progress > 0.1:
            self._draw_label(screen, hotspot, fonts.get('small'), progress)
        
        if hotspot.hover_progress > 0.3:
            self._draw_card(screen, hotspot, fonts, progress)

    def _ease_out(self, value):
        """柔化悬停动画曲线。"""
        value = max(0.0, min(1.0, value))
        return 1 - pow(1 - value, 3)

    def _draw_dot(self, screen, hotspot, time, progress):
        """绘制发光圆点（带呼吸闪烁效果）"""
        breath = math.sin(time * 2.2) * 0.5 + 0.5

        if hotspot.is_hovered:
            radius = self.base_radius + (self.hover_radius - self.base_radius) * progress
            alpha = int(255 * max(0.65, progress))
            glow_r = int(self.glow_radius * (0.75 + 0.35 * progress))
        else:
            if hotspot.hidden:
                base_alpha = 0.22 + breath * 0.12
            else:
                base_alpha = 0.52 + breath * 0.22

            radius = self.base_radius + breath * 1.8
            alpha = int(255 * base_alpha)
            glow_r = int(self.glow_radius * (0.5 + breath * 0.2))

        if hotspot.hidden and not hotspot.is_hovered:
            alpha = int(150 * alpha / 255)

        if hotspot.discovered:
            color = COLOR_DISCOVERED
        else:
            color = COLOR_CHAMPAGNE_LIGHT

        self._draw_glow_circle(screen, hotspot.dot_pos, color, radius, glow_r, alpha, progress)

    def _draw_glow_circle(self, screen, center, color, radius, glow_radius, alpha, progress):
        """绘制发光圆点"""
        cx, cy = center
        radius = int(radius)
        glow_radius = int(glow_radius)
        
        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        glow_center = (glow_radius, glow_radius)
        
        glow_alpha = int(alpha * (0.22 + 0.18 * progress))
        span = max(1, glow_radius - radius)
        for r in range(glow_radius, radius, -3):
            falloff = 1 - (r - radius) / span
            a = int(glow_alpha * falloff * falloff)
            pygame.draw.circle(glow_surface, (*color, max(0, a)), glow_center, r)
        
        screen.blit(glow_surface, (cx - glow_radius, cy - glow_radius))

        ring_radius = radius + int(4 * progress)
        pygame.draw.circle(screen, (*color, int(alpha * 0.35)), center, ring_radius, 2)
        pygame.draw.circle(screen, (*color, alpha), center, radius)

        inner_radius = max(2, radius // 2)
        pygame.draw.circle(screen, (255, 246, 218, min(255, alpha + 20)), center, inner_radius)
        highlight_pos = (int(cx - inner_radius * 0.35), int(cy - inner_radius * 0.35))
        pygame.draw.circle(screen, (255, 255, 255, int(alpha * 0.7)), highlight_pos, max(1, inner_radius // 3))

    def _draw_label(self, screen, hotspot, font, progress):
        """绘制胶囊标签"""
        if not font or progress < 0.1:
            return
            
        text = hotspot.title
        text_surface = font.render(text, True, COLOR_CHAMPAGNE_LIGHT)
        text_rect = text_surface.get_rect()
        
        padding_h = 12
        padding_v = 4
        
        label_width = text_rect.width + padding_h * 2
        label_height = text_rect.height + padding_v * 2
        
        dot_x, dot_y = hotspot.dot_pos
        radius = self.base_radius
        label_x = dot_x - label_width // 2
        label_y = dot_y - radius - label_height - 10 - int(6 * progress)
        
        surface = pygame.Surface((label_width, label_height), pygame.SRCALPHA)
        surface.fill((*COLOR_PANEL, int(190 * progress)))
        pygame.draw.rect(surface, (*COLOR_CHAMPAGNE, int(210 * progress)), 
                         (0, 0, label_width, label_height), 1, border_radius=10)
        
        screen.blit(surface, (label_x, label_y))
        text_surface.set_alpha(int(255 * progress))
        screen.blit(text_surface, (label_x + padding_h, label_y + padding_v))

    def _draw_card(self, screen, hotspot, fonts, progress):
        """绘制详情卡片"""
        if progress < 0.3:
            return
            
        title = hotspot.title
        desc = hotspot.desc
        
        font_title = fonts.get('title', fonts.get('small'))
        font_desc = fonts.get('desc', fonts.get('small'))
        
        title_surface = font_title.render(title, True, COLOR_CHAMPAGNE)
        max_text_width = 360
        desc_lines = self._wrap_text(desc, font_desc, max_text_width) if desc else []
        
        padding = 16
        desc_width = max([font_desc.size(line)[0] for line in desc_lines], default=0)
        card_width = min(420, max(220, max(title_surface.get_width(), desc_width) + padding * 2))
        title_height = title_surface.get_height()
        desc_height = len(desc_lines) * (font_desc.get_height() + 5)
        card_height = title_height + desc_height + padding * (3 if desc_lines else 2)
        
        dot_x, dot_y = hotspot.dot_pos
        card_x = dot_x - card_width // 2
        radius = self.base_radius
        card_y = dot_y - radius - card_height - 58 - int(10 * progress)
        
        card_x = max(12, min(card_x, SCREEN_WIDTH - card_width - 12))
        card_y = max(10, card_y)

        self._draw_connector(screen, (dot_x, dot_y - radius - 4), (card_x + card_width // 2, card_y + card_height), progress)
        
        surface = pygame.Surface((card_width, card_height), pygame.SRCALPHA)
        surface.fill((*COLOR_PANEL, int(218 * progress)))
        pygame.draw.rect(surface, (*COLOR_CHAMPAGNE, int(230 * progress)), 
                         (0, 0, card_width, card_height), 1, border_radius=8)
        pygame.draw.rect(surface, (*COLOR_PANEL_BORDER, int(90 * progress)),
                         (5, 5, card_width - 10, card_height - 10), 1, border_radius=6)
        
        screen.blit(surface, (card_x, card_y))
        title_surface.set_alpha(int(255 * progress))
        screen.blit(title_surface, (card_x + padding, card_y + padding))
        
        for i, line in enumerate(desc_lines):
            desc_surface = font_desc.render(line, True, COLOR_TEXT)
            desc_surface.set_alpha(int(235 * progress))
            y = card_y + padding + title_height + padding // 2 + i * (font_desc.get_height() + 5)
            screen.blit(desc_surface, (card_x + padding, y))

    def _draw_connector(self, screen, start, end, progress):
        """绘制热区与详情卡片之间的细连接线。"""
        alpha = int(120 * progress)
        if alpha <= 0:
            return

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.line(overlay, (*COLOR_CHAMPAGNE, alpha), start, end, 1)
        pygame.draw.circle(overlay, (*COLOR_CHAMPAGNE, alpha), end, 3)
        screen.blit(overlay, (0, 0))

    def _wrap_text(self, text, font, max_width):
        """按像素宽度包装文本，兼容中文和英文。"""
        if not text:
            return []

        lines = []
        for raw_line in text.splitlines():
            current = ""
            for char in raw_line:
                candidate = current + char
                if font.size(candidate)[0] <= max_width:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = char
            if current:
                lines.append(current)

        return lines
