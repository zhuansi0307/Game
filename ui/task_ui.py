"""
任务UI组件
负责显示任务提示、任务进度、任务日志等
"""

import pygame
from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_TEXT, COLOR_CHAMPAGNE, COLOR_PANEL, COLOR_PANEL_BORDER
from engine.asset_manager import AssetManager


class TaskUI:
    """任务系统UI组件"""

    def __init__(self):
        self.visible = False
        self.current_task = None
        
        self.notifications = []
        self.notification_duration = 3.0
        
        self.task_panel_visible = False
        self.task_list = []
        self.guidance = None
        self.asset_manager = AssetManager()
        self.fonts = {
            "notification": self.asset_manager.load_font(24),
            "panel_title": self.asset_manager.load_font(30),
            "task_title": self.asset_manager.load_font(22),
            "task_desc": self.asset_manager.load_font(18),
            "guidance_title": self.asset_manager.load_font(24),
            "guidance_hint": self.asset_manager.load_font(20),
        }

    def show_notification(self, message, duration=3.0):
        """
        显示任务通知
        :param message: 通知消息
        :param duration: 显示时长
        """
        self.notifications.append({
            "message": message,
            "duration": duration,
            "elapsed": 0.0,
            "progress": 0.0
        })

    def show_task_start(self, task):
        """显示任务开始通知"""
        message = f"新任务：{task.title}"
        self.show_notification(message, 4.0)

    def show_task_complete(self, task):
        """显示任务完成通知"""
        message = f"任务完成：{task.title}"
        self.show_notification(message, 4.0)

    def show_task_hint(self, hint):
        """显示任务提示"""
        message = f"提示：{hint}"
        self.show_notification(message, 3.0)

    def update_notifications(self, dt):
        """更新通知动画"""
        for notification in self.notifications[:]:
            notification["elapsed"] += dt
            notification["progress"] = min(1.0, notification["elapsed"] / notification["duration"])
            
            if notification["elapsed"] >= notification["duration"]:
                self.notifications.remove(notification)

    def update(self, dt):
        """更新UI"""
        self.update_notifications(dt)

    def draw(self, screen):
        """绘制任务UI"""
        if not self.visible and not self.notifications and not self.guidance:
            return

        self._draw_notifications(screen)
        self._draw_guidance(screen)
        
        if self.task_panel_visible:
            self._draw_task_panel(screen)

    def _draw_notifications(self, screen):
        """绘制通知列表"""
        if not self.notifications:
            return
            
        start_y = 80
        current_y = start_y
        
        for notification in self.notifications:
            height = self._draw_single_notification(
                screen, 
                notification, 
                current_y
            )
            current_y += height + 10

    def _draw_single_notification(self, screen, notification, y):
        """绘制单个通知"""
        progress = notification["progress"]
        
        if progress < 0.2:
            entry_progress = progress / 0.2
            alpha = entry_progress
            offset_x = int((1 - entry_progress) * 100)
        elif progress > 0.8:
            exit_progress = (progress - 0.8) / 0.2
            alpha = 1.0 - exit_progress
            offset_x = int(exit_progress * 100)
        else:
            alpha = 1.0
            offset_x = 0
        
        if alpha <= 0.01:
            return 0
        
        message = notification["message"]
        font = self.fonts["notification"]
        
        padding_h = 20
        padding_v = 12
        max_width = 430
        lines = self._wrap_text(message, font, max_width)
        line_height = font.get_height() + 4
        text_width = max((font.size(line)[0] for line in lines), default=0)
        width = min(max_width + padding_h * 2, max(180, text_width + padding_h * 2))
        height = len(lines) * line_height + padding_v * 2
        
        x = SCREEN_WIDTH - width - 20 + offset_x
        panel_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        panel_surface.fill((*COLOR_PANEL, int(200 * alpha)))
        pygame.draw.rect(panel_surface, (*COLOR_CHAMPAGNE, int(180 * alpha)), 
                         (0, 0, width, height), 1, border_radius=8)
        
        screen.blit(panel_surface, (x, y))
        for index, line in enumerate(lines):
            text_surface = font.render(line, True, COLOR_TEXT)
            text_surface.set_alpha(int(255 * alpha))
            screen.blit(text_surface, (x + padding_h, y + padding_v + index * line_height))
        return height

    def _draw_task_panel(self, screen):
        """绘制任务面板"""
        panel_width = 350
        panel_height = 500
        panel_x = SCREEN_WIDTH - panel_width - 20
        panel_y = 80
        
        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((*COLOR_PANEL, 220))
        pygame.draw.rect(panel_surface, (*COLOR_PANEL_BORDER, 255), 
                         (0, 0, panel_width, panel_height), 1, border_radius=12)
        
        screen.blit(panel_surface, (panel_x, panel_y))
        
        title_font = self.fonts["panel_title"]
        title_surface = title_font.render("任务", True, COLOR_CHAMPAGNE)
        screen.blit(title_surface, (panel_x + 20, panel_y + 20))
        
        if self.current_task:
            task_font = self.fonts["task_title"]
            task_title = self.current_task.title
            y_offset = panel_y + 70
            for line in self._wrap_text(task_title, task_font, panel_width - 40)[:3]:
                task_surface = task_font.render(line, True, COLOR_TEXT)
                screen.blit(task_surface, (panel_x + 20, y_offset))
                y_offset += task_font.get_height() + 4
            
            if self.current_task.description:
                desc_font = self.fonts["task_desc"]
                y_offset += 10
                for line in self._wrap_text(self.current_task.description, desc_font, panel_width - 40)[:6]:
                    desc_surface = desc_font.render(line, True, COLOR_PANEL_BORDER)
                    screen.blit(desc_surface, (panel_x + 20, y_offset))
                    y_offset += desc_font.get_height() + 4

    def hide(self):
        """隐藏所有UI"""
        self.visible = False
        self.notifications = []
        self.task_panel_visible = False
        self.guidance = None

    def set_guidance(self, guidance):
        """设置当前任务引导。"""
        self.guidance = guidance

    def _draw_guidance(self, screen):
        """绘制轻量任务引导面板。"""
        if not self.guidance:
            return

        panel_width = 460
        panel_height = 92
        panel_x = 30
        panel_y = SCREEN_HEIGHT - panel_height - 46

        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((*COLOR_PANEL, 205))
        pygame.draw.rect(
            panel_surface,
            (*COLOR_CHAMPAGNE, 165),
            (0, 0, panel_width, panel_height),
            1,
            border_radius=8,
        )
        screen.blit(panel_surface, (panel_x, panel_y))

        title_font = self.fonts["guidance_title"]
        hint_font = self.fonts["guidance_hint"]

        status = self.guidance.get("status", "")
        title = self.guidance.get("title", "")
        hint = self.guidance.get("hint", "")
        title_text = f"{status}：{title}" if status else title

        title_lines = self._wrap_text(title_text, title_font, panel_width - 36)[:1]
        if title_lines:
            title_surface = title_font.render(title_lines[0], True, COLOR_CHAMPAGNE)
            screen.blit(title_surface, (panel_x + 18, panel_y + 16))

        for index, line in enumerate(self._wrap_text(hint, hint_font, panel_width - 36)[:2]):
            hint_surface = hint_font.render(line, True, COLOR_TEXT)
            screen.blit(hint_surface, (panel_x + 18, panel_y + 48 + index * 22))

    def _wrap_text(self, text, font, max_width):
        if not text:
            return []

        lines = []
        current = ""
        for char in text:
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

    def set_current_task(self, task):
        """设置当前任务"""
        self.current_task = task
        self.visible = task is not None
        self.task_panel_visible = task is not None

    def clear_current_task(self):
        """清除当前任务"""
        self.current_task = None
        self.visible = False
        self.task_panel_visible = False
