"""
章节UI组件
负责章节推进、章节标题、章节进度等UI显示
"""

import pygame
import math
from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG_DARK, COLOR_TEXT, COLOR_CHAMPAGNE, COLOR_PANEL, COLOR_PANEL_BORDER


class ChapterUI:
    """章节推进UI组件"""

    def __init__(self):
        self.visible = False
        self.ui_type = None
        
        self.chapter_num = 0
        self.chapter_title = ""
        self.chapter_subtitle = ""
        self.chapter_description = ""
        
        self.progress = 0.0
        self.total_progress = 0.0
        
        self.animation_progress = 0.0
        self.animation_duration = 2.0
        
        self.show_progress = False
        self.show_complete = False
        self.complete_animation_progress = 0.0

    def show_chapter_start(self, chapter_num, title, subtitle="", description=""):
        """
        显示章节开始标题
        :param chapter_num: 章节编号
        :param title: 章节标题
        :param subtitle: 副标题
        :param description: 章节描述
        """
        self.visible = True
        self.ui_type = "chapter_start"
        
        self.chapter_num = chapter_num
        self.chapter_title = title
        self.chapter_subtitle = subtitle
        self.chapter_description = description
        
        self.animation_progress = 0.0
        self.animation_duration = 3.0
        
        self.show_progress = False

    def show_chapter_progress(self, current, total, chapter_title=""):
        """
        显示章节内进度
        :param current: 当前进度
        :param total: 总进度
        :param chapter_title: 章节标题
        """
        self.visible = True
        self.ui_type = "chapter_progress"
        
        self.progress = current
        self.total_progress = total
        self.chapter_title = chapter_title
        
        self.animation_progress = 1.0

    def show_chapter_complete(self, chapter_num, chapter_title):
        """
        显示章节完成
        :param chapter_num: 章节编号
        :param chapter_title: 章节标题
        """
        self.visible = True
        self.ui_type = "chapter_complete"
        
        self.chapter_num = chapter_num
        self.chapter_title = chapter_title
        
        self.complete_animation_progress = 0.0
        self.show_complete = True

    def update(self, dt):
        """更新动画"""
        if not self.visible:
            return
            
        if self.ui_type == "chapter_start" and self.animation_progress < 1.0:
            self.animation_progress += dt / self.animation_duration
            if self.animation_progress >= 1.0:
                self.animation_progress = 1.0
                
        elif self.ui_type == "chapter_complete" and self.show_complete:
            self.complete_animation_progress += dt * 0.8
            if self.complete_animation_progress >= 1.0:
                self.complete_animation_progress = 1.0

    def draw(self, screen):
        """绘制章节UI"""
        if not self.visible:
            return
            
        if self.ui_type == "chapter_start":
            self._draw_chapter_start(screen)
        elif self.ui_type == "chapter_progress":
            self._draw_chapter_progress(screen)
        elif self.ui_type == "chapter_complete":
            self._draw_chapter_complete(screen)

    def _draw_chapter_start(self, screen):
        """绘制章节开始标题"""
        progress = self.animation_progress
        
        fade_in = min(1.0, progress * 2)
        fade_out = 1.0 if progress < 0.7 else max(0.0, 1.0 - (progress - 0.7) / 0.3)
        alpha = fade_in * fade_out
        
        if alpha <= 0.01:
            return
            
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((*COLOR_BG_DARK, int(200 * alpha)))
        screen.blit(overlay, (0, 0))
        
        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2
        
        scale = 0.5 + progress * 0.5
        
        chapter_text = f"第{self._int_to_chinese(self.chapter_num)}章"
        chapter_font = pygame.font.Font(None, int(72 * scale))
        chapter_surface = chapter_font.render(chapter_text, True, COLOR_CHAMPAGNE)
        chapter_rect = chapter_surface.get_rect(center=(center_x, center_y - 80))
        
        title_font = pygame.font.Font(None, int(96 * scale))
        title_surface = title_font.render(self.chapter_title, True, COLOR_TEXT)
        title_rect = title_surface.get_rect(center=(center_x, center_y))
        
        if self.chapter_subtitle:
            subtitle_font = pygame.font.Font(None, int(36 * scale))
            subtitle_surface = subtitle_font.render(self.chapter_subtitle, True, COLOR_CHAMPAGNE)
            subtitle_rect = subtitle_surface.get_rect(center=(center_x, center_y + 70))
            
            subtitle_alpha = int(255 * alpha * min(1.0, (progress - 0.2) * 2))
            subtitle_surface.set_alpha(subtitle_alpha)
            screen.blit(subtitle_surface, subtitle_rect)
        
        chapter_alpha = int(255 * alpha)
        chapter_surface.set_alpha(chapter_alpha)
        title_surface.set_alpha(chapter_alpha)
        
        screen.blit(chapter_surface, chapter_rect)
        screen.blit(title_surface, title_rect)
        
        if self.chapter_description and progress > 0.5:
            desc_alpha = int(255 * alpha * min(1.0, (progress - 0.5) * 2))
            desc_font = pygame.font.Font(None, 28)
            desc_surface = desc_font.render(self.chapter_description, True, COLOR_PANEL_BORDER)
            desc_rect = desc_surface.get_rect(center=(center_x, center_y + 140))
            desc_surface.set_alpha(desc_alpha)
            screen.blit(desc_surface, desc_rect)

    def _draw_chapter_progress(self, screen):
        """绘制章节进度条"""
        if self.total_progress <= 0:
            return
            
        progress_ratio = self.progress / self.total_progress
        
        bar_width = 400
        bar_height = 8
        bar_x = (SCREEN_WIDTH - bar_width) // 2
        bar_y = SCREEN_HEIGHT - 100
        
        bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(screen, (*COLOR_PANEL_BORDER, 150), bg_rect, border_radius=4)
        
        progress_width = int(bar_width * progress_ratio)
        if progress_width > 0:
            progress_rect = pygame.Rect(bar_x, bar_y, progress_width, bar_height)
            pygame.draw.rect(screen, COLOR_CHAMPAGNE, progress_rect, border_radius=4)
        
        if self.chapter_title:
            font = pygame.font.Font(None, 24)
            text_surface = font.render(self.chapter_title, True, COLOR_PANEL_BORDER)
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, bar_y - 20))
            screen.blit(text_surface, text_rect)
        
        progress_text = f"{self.progress}/{self.total_progress}"
        progress_surface = font.render(progress_text, True, COLOR_CHAMPAGNE)
        progress_rect = progress_surface.get_rect(center=(SCREEN_WIDTH // 2, bar_y + bar_height + 20))
        screen.blit(progress_surface, progress_rect)

    def _draw_chapter_complete(self, screen):
        """绘制章节完成"""
        alpha = self.complete_animation_progress
        
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((*COLOR_BG_DARK, int(180 * alpha)))
        screen.blit(overlay, (0, 0))
        
        center_x = SCREEN_WIDTH // 2
        center_y = SCREEN_HEIGHT // 2
        
        complete_text = "章节完成"
        font = pygame.font.Font(None, 64)
        complete_surface = font.render(complete_text, True, COLOR_CHAMPAGNE)
        complete_rect = complete_surface.get_rect(center=(center_x, center_y - 30))
        
        chapter_text = f"第{self._int_to_chinese(self.chapter_num)}章"
        sub_font = pygame.font.Font(None, 36)
        chapter_surface = sub_font.render(chapter_text, True, COLOR_TEXT)
        chapter_rect = chapter_surface.get_rect(center=(center_x, center_y + 40))
        
        complete_surface.set_alpha(int(255 * alpha))
        chapter_surface.set_alpha(int(255 * alpha))
        
        screen.blit(complete_surface, complete_rect)
        screen.blit(chapter_surface, chapter_rect)

    def _int_to_chinese(self, num):
        """数字转中文"""
        chinese_nums = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
        if num <= 10:
            return chinese_nums[num]
        elif num < 100:
            tens = num // 10
            ones = num % 10
            if tens == 1:
                return chinese_nums[10] + (chinese_nums[ones] if ones > 0 else '')
            else:
                return chinese_nums[tens] + chinese_nums[10] + (chinese_nums[ones] if ones > 0 else '')
        return str(num)

    def is_animation_finished(self):
        """检查动画是否完成"""
        if self.ui_type == "chapter_start":
            return self.animation_progress >= 1.0
        elif self.ui_type == "chapter_complete":
            return self.complete_animation_progress >= 1.0
        return True

    def hide(self):
        """隐藏UI"""
        self.visible = False
        self.ui_type = None
        self.show_complete = False
