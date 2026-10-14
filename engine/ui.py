"""
通用UI组件模块
提供基础绘图函数用于绘制文本、按钮、面板等UI元素
采用现代都市写实恋爱视觉小说风格

注意：热区相关渲染已迁移到 ui/hotspot_ui.py
"""

import pygame
from .constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    COLOR_TEXT, COLOR_TEXT_MUTED, COLOR_CHAMPAGNE, COLOR_CHAMPAGNE_BRIGHT,
    COLOR_PANEL, COLOR_PANEL_BORDER, COLOR_DIALOGUE_BG, COLOR_DIALOGUE_BORDER
)


def draw_text(screen, text, font, color, pos, max_width=None):
    """
    在屏幕上绘制文本
    :param screen: pygame屏幕surface
    :param text: 要绘制的文本
    :param font: pygame字体对象
    :param color: 文本颜色 (R, G, B)
    :param pos: 文本位置 (x, y)
    :param max_width: 最大宽度，超过后自动换行
    :return: 文本占据的矩形区域
    """
    if max_width:
        lines = text.split('\n')
        x, y = pos
        line_height = font.get_height()
        total_height = 0

        for line in lines:
            if line.strip() == '':
                y += line_height
                total_height += line_height
                continue
            words_in_line = line.split()
            current_line = ''
            for w in words_in_line:
                test_line = current_line + w + ' '
                if font.size(test_line)[0] <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        text_surface = font.render(current_line.strip(), True, color)
                        screen.blit(text_surface, (x, y + total_height))
                        total_height += line_height
                    current_line = w + ' '
            if current_line:
                text_surface = font.render(current_line.strip(), True, color)
                screen.blit(text_surface, (x, y + total_height))
            total_height += line_height

        return pygame.Rect(pos[0], pos[1], max_width, total_height)
    else:
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(topleft=pos)
        screen.blit(text_surface, text_rect)
        return text_rect


def draw_button(screen, rect, text, font, hovered=False):
    """绘制按钮"""
    x, y, width, height = rect
    bg_color = COLOR_PANEL
    border_color = COLOR_CHAMPAGNE_BRIGHT if hovered else COLOR_CHAMPAGNE
    border_width = 2 if hovered else 1

    button_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    button_surface.fill((*bg_color, 200))
    pygame.draw.rect(button_surface, (*border_color, 255),
                     (0, 0, width, height), border_width)
    screen.blit(button_surface, (x, y))

    text_color = COLOR_CHAMPAGNE_BRIGHT if hovered else COLOR_CHAMPAGNE
    text_surface = font.render(text, True, text_color)
    text_rect = text_surface.get_rect(center=(x + width // 2, y + height // 2))
    screen.blit(text_surface, text_rect)

    return pygame.Rect(x, y, width, height)


def draw_panel(screen, rect, alpha=160, border=True):
    """绘制半透明面板"""
    x, y, width, height = rect

    panel_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    panel_surface.fill((*COLOR_PANEL, alpha))

    if border:
        pygame.draw.rect(panel_surface, (*COLOR_PANEL_BORDER, 255),
                        (0, 0, width, height), 1)

    screen.blit(panel_surface, (x, y))
    return pygame.Rect(x, y, width, height)


def draw_dialogue_box(screen, speaker, text, font_speaker=None, font_text=None, asset_manager=None):
    """绘制对话框"""
    if font_speaker is None:
        font_speaker = asset_manager.load_font(28) if asset_manager else pygame.font.Font(None, 28)
    if font_text is None:
        font_text = asset_manager.load_font(32) if asset_manager else pygame.font.Font(None, 32)

    box_width = SCREEN_WIDTH - 200
    box_height = 180
    box_x = 100
    box_y = SCREEN_HEIGHT - box_height - 60

    box_surface = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
    box_surface.fill((*COLOR_DIALOGUE_BG, 230))
    pygame.draw.rect(box_surface, (*COLOR_DIALOGUE_BORDER, 255),
                    (0, 0, box_width, box_height), 2)
    pygame.draw.rect(box_surface, (*COLOR_PANEL_BORDER, 100),
                    (6, 6, box_width - 12, box_height - 12), 1)
    screen.blit(box_surface, (box_x, box_y))

    speaker_color = COLOR_CHAMPAGNE
    speaker_surface = font_speaker.render(speaker, True, speaker_color)
    screen.blit(speaker_surface, (box_x + 30, box_y + 20))

    line_y = box_y + 55
    pygame.draw.line(screen, (*COLOR_CHAMPAGNE, 100),
                    (box_x + 30, line_y), (box_x + box_width - 30, line_y), 1)

    draw_text(screen, text, font_text, COLOR_TEXT, (box_x + 30, box_y + 70), box_width - 60)


def draw_menu_button(screen, rect, text, font, hovered=False, icon=None, hover_progress=None):
    """绘制菜单按钮"""
    x, y, width, height = rect

    if hover_progress is None:
        hover_progress = 1.0 if hovered else 0.0

    bg_alpha = int(180 + 40 * hover_progress)

    c1 = COLOR_CHAMPAGNE
    c2 = COLOR_CHAMPAGNE_BRIGHT
    border_r = int(c1[0] + (c2[0] - c1[0]) * hover_progress)
    border_g = int(c1[1] + (c2[1] - c1[1]) * hover_progress)
    border_b = int(c1[2] + (c2[2] - c1[2]) * hover_progress)
    border_color = (border_r, border_g, border_b)

    border_width = 1 if hover_progress < 0.5 else 2

    expand = int(20 * hover_progress)
    draw_x = x - expand // 2
    draw_w = width + expand

    button_surface = pygame.Surface((draw_w, height), pygame.SRCALPHA)
    button_surface.fill((*COLOR_PANEL, bg_alpha))
    pygame.draw.rect(button_surface, (*border_color, 255), (0, 0, draw_w, height), border_width)

    if hover_progress > 0:
        inner_rect = (3, 3, draw_w - 6, height - 6)
        pygame.draw.rect(button_surface, (*border_color, int(30 * hover_progress)), inner_rect, 1)

    screen.blit(button_surface, (draw_x, y))

    text_color = border_color
    text_surface = font.render(text, True, text_color)
    text_x = draw_x + 30 + int(10 * hover_progress)
    if icon:
        text_x += 40
    text_y = y + (height - text_surface.get_height()) // 2
    screen.blit(text_surface, (text_x, text_y))

    if icon:
        icon_x = draw_x + 20 + int(10 * hover_progress)
        icon_y = y + (height - icon.get_height()) // 2
        screen.blit(icon, (icon_x, icon_y))

    return pygame.Rect(x, y, width, height)


def draw_tooltip(screen, text, pos, font, bg_color=None, text_color=None):
    """绘制提示框"""
    if bg_color is None:
        bg_color = (*COLOR_PANEL, 240)
    if text_color is None:
        text_color = COLOR_TEXT

    text_surface = font.render(text, True, text_color)
    padding = 10
    width = text_surface.get_width() + padding * 2
    height = text_surface.get_height() + padding * 2

    tooltip_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    tooltip_surface.fill(bg_color)
    pygame.draw.rect(tooltip_surface, (*COLOR_CHAMPAGNE, 150), (0, 0, width, height), 1)

    screen.blit(tooltip_surface, pos)
    screen.blit(text_surface, (pos[0] + padding, pos[1] + padding))


def draw_rounded_panel(screen, rect, bg_color, border_color=None, border_width=1, radius=18, border_alpha=255):
    """
    绘制圆角面板
    :param screen: pygame屏幕surface
    :param rect: 面板区域 (x, y, width, height)
    :param bg_color: 背景颜色 (R, G, B)
    :param border_color: 边框颜色
    :param border_width: 边框宽度
    :param radius: 圆角半径
    :param border_alpha: 边框透明度
    """
    x, y, width, height = rect

    panel_surface = pygame.Surface((width, height), pygame.SRCALPHA)

    if len(bg_color) == 4:
        panel_surface.fill(bg_color)
    else:
        panel_surface.fill((*bg_color, 240))

    if border_color:
        if len(border_color) == 4:
            pygame.draw.rect(panel_surface, border_color, (0, 0, width, height), border_width, border_radius=radius)
        else:
            pygame.draw.rect(panel_surface, (*border_color, border_alpha), (0, 0, width, height), border_width, border_radius=radius)

    screen.blit(panel_surface, (x, y))


def draw_text_wrapped(screen, text, font, color, rect, line_spacing=6):
    """
    绘制自动换行的文本
    :param screen: pygame屏幕surface（可以为None用于计算高度）
    :param text: 文本内容
    :param font: 字体对象
    :param color: 文字颜色
    :param rect: 限制区域 (x, y, width, height)
    :param line_spacing: 行间距
    """
    x, y, max_width, max_height = rect
    line_height = font.get_height() + line_spacing

    words = text.split('\n')
    current_y = y

    for line in words:
        if line.strip() == '':
            current_y += line_height
            continue

        words_in_line = line.split()
        current_line = ''
        words_to_render = []

        for w in words_in_line:
            test_line = current_line + w + ' '
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    words_to_render.append(current_line.strip())
                current_line = w + ' '

        if current_line:
            words_to_render.append(current_line.strip())

        for wl in words_to_render:
            if current_y - y + line_height > max_height:
                break
            text_surface = font.render(wl, True, color)
            if screen is not None:
                screen.blit(text_surface, (x, current_y))
            current_y += line_height

    return current_y - y


def draw_slider(screen, rect, value, font=None, label=None, min_value=0, max_value=100):
    """
    绘制滑动条
    :param screen: pygame屏幕surface
    :param rect: 滑动条区域 (x, y, width, height)
    :param value: 当前值 (min_value ~ max_value)
    :param font: 字体（用于显示标签和数值）
    :param label: 标签文本
    :param min_value: 最小值
    :param max_value: 最大值
    :return: (knob_rect, current_value) - 滑块区域和当前值
    """
    x, y, width, height = rect

    # 轨道（背景条）
    track_height = 10
    track_y = y + (height - track_height) // 2
    track_rect = pygame.Rect(x, track_y, width, track_height)
    track_surface = pygame.Surface((width, track_height), pygame.SRCALPHA)
    track_surface.fill((*COLOR_PANEL_BORDER, 200))
    pygame.draw.rect(track_surface, (*COLOR_CHAMPAGNE, 100),
                     (0, 0, width, track_height), 0, track_height // 2)
    screen.blit(track_surface, (x, track_y))

    # 计算滑块位置
    ratio = (value - min_value) / (max_value - min_value) if max_value != min_value else 0
    knob_width = 24
    knob_height = height
    knob_x = x + int(ratio * (width - knob_width))

    # 滑块
    knob_rect = pygame.Rect(knob_x, y, knob_width, knob_height)
    knob_color = COLOR_CHAMPAGNE_BRIGHT
    knob_surface = pygame.Surface((knob_width, knob_height), pygame.SRCALPHA)
    knob_surface.fill((*knob_color, 230))
    pygame.draw.rect(knob_surface, (*COLOR_CHAMPAGNE, 255),
                     (0, 0, knob_width, knob_height), 2, knob_height // 2)
    screen.blit(knob_surface, (knob_x, y))

    # 标签和数值显示
    if font:
        if label:
            display_text = f"{label}: {int(value)}"
        else:
            display_text = str(int(value))
        text_surface = font.render(display_text, True, COLOR_CHAMPAGNE)
        screen.blit(text_surface, (x, y - 40))

    return knob_rect, value
