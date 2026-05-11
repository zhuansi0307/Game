"""
3D glass HUD for exploration scenes.

The scene background and hotspots still render through pygame surfaces; this
module draws the final interactive HUD overlay directly in OpenGL so the hover
tilt and scale effects from ui/refer/button.py are preserved.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import pygame
from OpenGL.GL import (
    GL_BLEND,
    GL_CLAMP_TO_EDGE,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_LINEAR,
    GL_LINE_SMOOTH,
    GL_LINE_SMOOTH_HINT,
    GL_MODELVIEW,
    GL_MULTISAMPLE,
    GL_NICEST,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_POLYGON_SMOOTH,
    GL_POLYGON_SMOOTH_HINT,
    GL_PROJECTION,
    GL_QUADS,
    GL_RGBA,
    GL_SRC_ALPHA,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_UNSIGNED_BYTE,
    glBegin,
    glBindTexture,
    glBlendFunc,
    glClear,
    glColor4f,
    glDeleteTextures,
    glDisable,
    glEnable,
    glEnd,
    glGenTextures,
    glHint,
    glLoadIdentity,
    glMatrixMode,
    glOrtho,
    glPopMatrix,
    glPushMatrix,
    glRotatef,
    glScalef,
    glTexCoord2f,
    glTexImage2D,
    glTexParameteri,
    glTranslatef,
    glVertex3f,
    glViewport,
)

from engine.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from engine.game_state import get_game_state


TEXTURE_SCALE = 3

COLORS = {
    "ink": (51, 65, 85),
    "muted": (100, 116, 139),
    "slate_400": (148, 163, 184),
    "white": (255, 255, 255),
    "pink": (244, 114, 182),
    "pink_edge": (251, 207, 232),
    "sky": (56, 189, 248),
    "purple": (192, 132, 252),
    "purple_fill": (233, 213, 255),
    "green": (52, 211, 153),
    "green_fill": (167, 243, 208),
    "blue": (96, 165, 250),
    "blue_fill": (191, 219, 254),
    "amber": (251, 191, 36),
    "orange": (249, 115, 22),
    "rose": (251, 113, 133),
    "indigo": (129, 140, 248),
}

TIME_STATES = {
    "morning": {
        "label": "早上",
        "kind": "sun",
        "color": COLORS["amber"],
        "fill": (253, 230, 138),
        "shadow": COLORS["sky"],
    },
    "noon": {
        "label": "中午",
        "kind": "sun",
        "color": COLORS["orange"],
        "fill": (254, 215, 170),
        "shadow": COLORS["orange"],
    },
    "afternoon": {
        "label": "下午",
        "kind": "sunset",
        "color": COLORS["rose"],
        "fill": (254, 205, 211),
        "shadow": (244, 63, 94),
    },
    "evening": {
        "label": "晚上",
        "kind": "moon",
        "color": COLORS["indigo"],
        "fill": (199, 210, 254),
        "shadow": (99, 102, 241),
    },
}

FONT_CACHE: dict[tuple[int, bool], pygame.font.Font] = {}


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key in FONT_CACHE:
        return FONT_CACHE[key]

    candidates = [
        "M PLUS Rounded 1c",
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial",
    ]
    for name in candidates:
        path = pygame.font.match_font(name, bold=bold)
        if path:
            FONT_CACHE[key] = pygame.font.Font(path, size)
            return FONT_CACHE[key]

    FONT_CACHE[key] = pygame.font.Font(None, size)
    return FONT_CACHE[key]


def exp_smooth(current: float, target: float, speed: float, dt: float) -> float:
    return target + (current - target) * math.exp(-speed * dt)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def text_width(text: str, size: int, bold: bool = False) -> int:
    return math.ceil(get_font(size * TEXTURE_SCALE, bold).size(text)[0] / TEXTURE_SCALE)


def wrap_text(text: str, size: int, max_width: int, bold: bool = False, max_lines: int | None = None) -> list[str]:
    if not text:
        return []

    font = get_font(size * TEXTURE_SCALE, bold)
    limit = max_width * TEXTURE_SCALE
    lines: list[str] = []
    for raw_line in str(text).splitlines():
        current = ""
        for char in raw_line:
            candidate = current + char
            if font.size(candidate)[0] <= limit:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = char
            if max_lines is not None and len(lines) >= max_lines:
                return lines
        if current:
            lines.append(current)
        if max_lines is not None and len(lines) >= max_lines:
            return lines
    return lines


class Painter:
    def __init__(self, logical_width: int, logical_height: int, scale: int = TEXTURE_SCALE):
        self.logical_width = logical_width
        self.logical_height = logical_height
        self.scale = scale
        self.surface = pygame.Surface((logical_width * scale, logical_height * scale), pygame.SRCALPHA)

    def n(self, value: float) -> int:
        return round(value * self.scale)

    def point(self, point: tuple[float, float]) -> tuple[int, int]:
        return self.n(point[0]), self.n(point[1])

    def rect(self, rect: pygame.Rect | tuple[float, float, float, float]) -> pygame.Rect:
        x, y, w, h = rect
        return pygame.Rect(self.n(x), self.n(y), self.n(w), self.n(h))

    def rounded(
        self,
        rect: pygame.Rect | tuple[float, float, float, float],
        color: tuple[int, int, int] | tuple[int, int, int, int],
        radius: float,
        border: tuple[int, int, int] | tuple[int, int, int, int] | None = None,
        border_width: float = 1,
    ) -> None:
        scaled = self.rect(rect)
        pygame.draw.rect(self.surface, color, scaled, border_radius=self.n(radius))
        if border:
            pygame.draw.rect(self.surface, border, scaled, self.n(border_width), border_radius=self.n(radius))

    def circle(
        self,
        color: tuple[int, int, int] | tuple[int, int, int, int],
        center: tuple[float, float],
        radius: float,
        width: float = 0,
    ) -> None:
        pygame.draw.circle(self.surface, color, self.point(center), self.n(radius), self.n(width) if width else 0)

    def line(
        self,
        color: tuple[int, int, int] | tuple[int, int, int, int],
        start: tuple[float, float],
        end: tuple[float, float],
        width: float = 1,
    ) -> None:
        pygame.draw.line(self.surface, color, self.point(start), self.point(end), self.n(width))

    def polygon(
        self,
        color: tuple[int, int, int] | tuple[int, int, int, int],
        points: list[tuple[float, float]],
        width: float = 0,
    ) -> None:
        pygame.draw.polygon(self.surface, color, [self.point(point) for point in points], self.n(width) if width else 0)

    def arc(
        self,
        color: tuple[int, int, int] | tuple[int, int, int, int],
        rect: pygame.Rect | tuple[float, float, float, float],
        start: float,
        end: float,
        width: float = 1,
    ) -> None:
        pygame.draw.arc(self.surface, color, self.rect(rect), start, end, self.n(width))

    def text(
        self,
        text: str,
        size: int,
        color: tuple[int, int, int] | tuple[int, int, int, int],
        pos: tuple[float, float],
        anchor: str = "center",
        bold: bool = False,
    ) -> None:
        font = get_font(size * self.scale, bold)
        image = font.render(str(text), True, color)
        rect = image.get_rect()
        setattr(rect, anchor, self.point(pos))
        self.surface.blit(image, rect)


def draw_glass(
    painter: Painter,
    rect: pygame.Rect,
    radius: int,
    shadow_rgb: tuple[int, int, int],
    bg_alpha: int = 116,
    shadow_strength: int = 38,
) -> None:
    for layer in range(7, 0, -1):
        spread = layer * 4
        alpha = max(2, shadow_strength // (layer + 1))
        shadow_rect = rect.inflate(spread * 2, spread * 2)
        shadow_rect.x += 4
        shadow_rect.y += 7
        painter.rounded(shadow_rect, (*shadow_rgb, alpha), radius + spread)

    painter.rounded(rect, (255, 255, 255, bg_alpha), radius)
    pygame.draw.rect(
        painter.surface,
        (255, 255, 255, 230),
        painter.rect(rect),
        painter.n(1),
        border_radius=painter.n(radius),
    )
    painter.line((255, 255, 255, 180), (rect.x + radius, rect.y + 2), (rect.right - radius, rect.y + 2), 1)
    painter.line((0, 0, 0, 18), (rect.x + radius, rect.bottom - 2), (rect.right - radius, rect.bottom - 2), 1)


def draw_start_menu_card(
    painter: Painter,
    rect: pygame.Rect,
    radius: int = 24,
    bg_alpha: int = 120,
    border_alpha: int = 180,
) -> None:
    """Draw the same simple glass card used by ui/refer/main.py."""
    painter.rounded(rect, (255, 255, 255, bg_alpha), radius)
    pygame.draw.rect(
        painter.surface,
        (255, 255, 255, border_alpha),
        painter.rect(rect),
        width=painter.n(2),
        border_radius=painter.n(radius),
    )


def draw_neumorphic_card(
    painter: Painter,
    rect: pygame.Rect,
    radius: int,
    tint: tuple[int, int, int] = (238, 247, 255),
    bg_alpha: int = 176,
    shadow_rgb: tuple[int, int, int] = (51, 65, 85),
) -> None:
    """Opaque soft skeuomorphic card used by the redesigned in-game HUD."""
    for layer in range(8, 0, -1):
        spread = layer * 3
        alpha = max(2, 32 // (layer + 1))
        shadow = rect.inflate(spread * 2, spread * 2)
        shadow.x += 6
        shadow.y += 9
        painter.rounded(shadow, (*shadow_rgb, alpha), radius + spread)

    painter.rounded(rect, (*tint, 255), radius)
    painter.rounded(rect.inflate(-6, -6), (255, 255, 255, 86), max(4, radius - 5))
    pygame.draw.rect(
        painter.surface,
        (255, 255, 255, 230),
        painter.rect(rect),
        painter.n(1.5),
        border_radius=painter.n(radius),
    )
    pygame.draw.rect(
        painter.surface,
        (64, 124, 196, 72),
        painter.rect(rect.inflate(-2, -2)),
        painter.n(1),
        border_radius=painter.n(max(2, radius - 1)),
    )
    painter.line((255, 255, 255, 210), (rect.x + radius, rect.y + 3), (rect.right - radius, rect.y + 3), 1.4)
    painter.line((37, 99, 235, 96), (rect.x + radius, rect.bottom - 4), (rect.right - radius, rect.bottom - 4), 1.8)


def draw_skeuo_hourglass(p: Painter, center: tuple[float, float], color: tuple[int, int, int]) -> None:
    x, y = center
    p.rounded((x - 19, y - 25, 38, 8), (255, 255, 255, 230), 4)
    p.rounded((x - 18, y + 17, 36, 8), (148, 163, 184, 235), 4)
    p.line((148, 163, 184, 230), (x - 14, y - 18), (x + 14, y + 18), 2.2)
    p.line((255, 255, 255, 220), (x + 14, y - 18), (x - 14, y + 18), 2.2)
    p.polygon((255, 255, 255, 86), [(x - 13, y - 17), (x + 13, y - 17), (x, y - 2)])
    p.polygon((255, 255, 255, 76), [(x - 13, y + 17), (x + 13, y + 17), (x, y + 2)])
    p.polygon((245, 158, 11, 238), [(x - 10, y - 14), (x + 10, y - 14), (x, y - 4)])
    p.polygon((251, 191, 36, 246), [(x - 11, y + 16), (x + 11, y + 16), (x, y + 5)])
    p.line((255, 255, 255, 190), (x - 8, y - 13), (x + 7, y - 13), 1.2)


def draw_skeuo_map(p: Painter, center: tuple[float, float], color: tuple[int, int, int]) -> None:
    x, y = center
    shadow = (15, 23, 42, 38)
    p.polygon(shadow, [(x - 23, y - 12), (x - 7, y - 21), (x - 7, y + 20), (x - 23, y + 27)])
    p.polygon((209, 250, 229), [(x - 24, y - 17), (x - 8, y - 24), (x - 8, y + 17), (x - 24, y + 24)])
    p.polygon((52, 211, 153), [(x - 7, y - 24), (x + 8, y - 16), (x + 8, y + 25), (x - 7, y + 17)])
    p.polygon((187, 247, 208), [(x + 9, y - 16), (x + 25, y - 24), (x + 25, y + 17), (x + 9, y + 25)])
    p.line((255, 255, 255, 230), (x - 8, y - 23), (x - 8, y + 17), 2)
    p.line((255, 255, 255, 210), (x + 8, y - 16), (x + 8, y + 24), 2)
    p.line((22, 101, 52, 82), (x - 20, y - 4), (x - 12, y - 8), 1.2)
    p.line((22, 101, 52, 82), (x + 13, y + 6), (x + 22, y + 1), 1.2)
    p.circle((255, 255, 255, 170), (x - 17, y - 13), 3)


def draw_skeuo_profile(p: Painter, center: tuple[float, float], color: tuple[int, int, int]) -> None:
    x, y = center
    p.circle((15, 23, 42, 34), (x + 3, y + 5), 24)
    p.circle((147, 197, 253), (x, y - 11), 10)
    p.circle((96, 165, 250), (x - 1, y - 12), 8)
    p.circle((255, 255, 255, 150), (x - 4, y - 16), 3)
    p.rounded((x - 22, y + 3, 44, 27), (191, 219, 254), 15)
    p.rounded((x - 17, y + 7, 34, 18), (96, 165, 250), 12)
    p.line((255, 255, 255, 180), (x - 13, y + 10), (x + 13, y + 10), 1.5)


def draw_skeuo_hotspot(p: Painter, center: tuple[float, float], color: tuple[int, int, int], progress: float, pulse: float) -> None:
    x, y = center
    glow = round(54 + 50 * progress + 18 * pulse)
    p.circle((*color, round(42 + 58 * progress)), (x, y), glow, 2.0)
    p.circle((15, 23, 42, 42), (x + 5, y + 8), 25)
    p.circle((255, 255, 255, 205), (x, y), 24)
    p.circle((*color, 218), (x, y), 17 + progress * 3)
    p.circle((255, 255, 255, 210), (x - 6, y - 7), 6)
    p.circle((255, 255, 255, 110), (x + 5, y + 5), 9, 2)
    p.polygon((255, 255, 255, 210), [(x, y - 26), (x + 7, y - 13), (x - 7, y - 13)])


def draw_skeuo_exclamation_hotspot(p: Painter, center: tuple[float, float], progress: float, pulse: float) -> None:
    x, y = center
    color = (248, 113, 113)
    p.circle((*color, round(50 + 72 * pulse)), (x, y), 34 + progress * 8, 2)
    p.circle((255, 255, 255, 215), (x, y), 27)
    p.circle((254, 226, 226), (x, y), 22)
    p.rounded((x - 5, y - 17, 10, 23), color, 5)
    p.circle(color, (x, y + 14), 6)
    p.line((255, 255, 255, 180), (x - 3, y - 14), (x - 3, y + 2), 1.5)


def upload_texture(surface: pygame.Surface) -> int:
    texture = glGenTextures(1)
    if isinstance(texture, (list, tuple)):
        texture = int(texture[0])
    else:
        texture = int(texture)

    glBindTexture(GL_TEXTURE_2D, texture)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    data = pygame.image.tobytes(surface, "RGBA", True)
    width, height = surface.get_size()
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    return texture


def draw_surface_gl(
    surface: pygame.Surface,
    x: float,
    y: float,
    width: float,
    height: float,
    alpha: float = 1.0,
    rot_x: float = 0.0,
    rot_y: float = 0.0,
    scale: float = 1.0,
    z: float = 0.0,
) -> None:
    if alpha <= 0.01:
        return

    texture = upload_texture(surface)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture)
    glColor4f(1.0, 1.0, 1.0, clamp(alpha, 0.0, 1.0))

    cx = x + width / 2
    cy = y + height / 2
    hw = width / 2
    hh = height / 2

    glPushMatrix()
    glTranslatef(cx, cy, z)
    glScalef(scale, scale, 1.0)
    glRotatef(rot_x, 1.0, 0.0, 0.0)
    glRotatef(rot_y, 0.0, 1.0, 0.0)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 1)
    glVertex3f(-hw, -hh, 0)
    glTexCoord2f(1, 1)
    glVertex3f(hw, -hh, 0)
    glTexCoord2f(1, 0)
    glVertex3f(hw, hh, 0)
    glTexCoord2f(0, 0)
    glVertex3f(-hw, hh, 0)
    glEnd()
    glPopMatrix()

    glBindTexture(GL_TEXTURE_2D, 0)
    try:
        glDeleteTextures([texture])
    except TypeError:
        glDeleteTextures(1, [texture])


def draw_pin_icon(p: Painter, center: tuple[float, float], color: tuple[int, int, int]) -> None:
    x, y = center
    p.circle(color, (x, y - 4), 7)
    p.polygon(color, [(x - 6, y), (x + 6, y), (x, y + 11)])
    p.circle(COLORS["white"], (x, y - 4), 3)


def draw_star_icon(p: Painter, center: tuple[float, float], color: tuple[int, int, int]) -> None:
    x, y = center
    points = []
    for index in range(10):
        radius = 13 if index % 2 == 0 else 6
        angle = -math.pi / 2 + index * math.pi / 5
        points.append((x + math.cos(angle) * radius, y + math.sin(angle) * radius))
    p.polygon(color, points)
    p.polygon(COLORS["pink_edge"], points, 1.5)


def draw_tool_hourglass(p: Painter, center: tuple[float, float], color: tuple[int, int, int]) -> None:
    x, y = center
    p.line((255, 255, 255), (x - 8, y - 13), (x + 8, y - 13), 2)
    p.line((255, 255, 255), (x - 8, y + 13), (x + 8, y + 13), 2)
    p.polygon(COLORS["purple_fill"], [(x - 8, y - 12), (x + 8, y - 12), (x, y - 2)])
    p.polygon(color, [(x - 8, y + 12), (x + 8, y + 12), (x, y + 2)])
    p.line((255, 255, 255), (x - 7, y - 10), (x + 7, y + 10), 1.5)
    p.line((255, 255, 255), (x + 7, y - 10), (x - 7, y + 10), 1.5)


def draw_tool_map(p: Painter, center: tuple[float, float], color: tuple[int, int, int]) -> None:
    x, y = center
    p.polygon(COLORS["green_fill"], [(x - 15, y - 10), (x - 5, y - 15), (x - 5, y + 11), (x - 15, y + 16)])
    p.polygon(color, [(x - 4, y - 15), (x + 6, y - 10), (x + 6, y + 16), (x - 4, y + 11)])
    p.polygon(COLORS["green_fill"], [(x + 7, y - 10), (x + 16, y - 15), (x + 16, y + 11), (x + 7, y + 16)])
    p.line((255, 255, 255), (x - 5, y - 15), (x - 5, y + 11), 1.5)
    p.line((255, 255, 255), (x + 6, y - 10), (x + 6, y + 16), 1.5)


def draw_tool_user(p: Painter, center: tuple[float, float], color: tuple[int, int, int]) -> None:
    x, y = center
    p.circle(color, (x, y - 8), 6)
    p.circle(COLORS["blue_fill"], (x, y + 9), 12)
    p.rounded((x - 14, y + 8, 28, 10), COLORS["blue_fill"], 5)
    p.line((255, 255, 255), (x - 14, y + 17), (x + 14, y + 17), 2)


def draw_time_icon(
    p: Painter,
    center: tuple[float, float],
    kind: str,
    stroke: tuple[int, int, int],
    fill: tuple[int, int, int],
) -> None:
    x, y = center
    if kind == "sun":
        p.circle(fill, (x, y), 6)
        p.circle(stroke, (x, y), 6, 2)
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            p.line(stroke, (x + math.cos(rad) * 11, y + math.sin(rad) * 11), (x + math.cos(rad) * 14, y + math.sin(rad) * 14), 2)
    elif kind == "sunset":
        p.arc(stroke, (x - 11, y - 10, 22, 20), math.pi, 0, 2.5)
        p.line(stroke, (x - 14, y + 5), (x + 14, y + 5), 2.5)
        p.line(stroke, (x - 9, y + 10), (x + 9, y + 10), 2)
        p.line(stroke, (x, y - 14), (x, y - 11), 2)
        p.line(stroke, (x - 11, y - 5), (x - 8, y - 2), 2)
        p.line(stroke, (x + 11, y - 5), (x + 8, y - 2), 2)
    else:
        p.circle(fill, (x, y), 11)
        p.circle((255, 255, 255, 210), (x + 5, y - 4), 11)
        p.polygon(stroke, [(x + 7, y + 3), (x + 9, y + 7), (x + 13, y + 8), (x + 9, y + 10), (x + 7, y + 14), (x + 5, y + 10), (x + 1, y + 8), (x + 5, y + 7)])


@dataclass
class ButtonState:
    hover: float = 0.0
    press: float = 0.0
    flash: float = 0.0

    def update(self, inside: bool, mouse_down: bool, dt: float) -> None:
        self.hover = exp_smooth(self.hover, 1.0 if inside else 0.0, 18.0, dt)
        self.press = exp_smooth(self.press, 1.0 if inside and mouse_down else 0.0, 24.0, dt)
        self.flash = max(0.0, self.flash - dt * 3.5)

    def click(self) -> None:
        self.flash = 1.0


class ScenePill:
    def __init__(self) -> None:
        self.rect = pygame.Rect(32, 110, 276, 60)
        self.state = ButtonState()
        self.text = ""

    def update(self, mouse: tuple[int, int], down: bool, title: str, dt: float) -> None:
        self.text = title or "当前位置"
        width = max(250, min(440, text_width(self.text, 20, True) + 116))
        self.rect.width = width
        self.state.update(self.rect.collidepoint(mouse), down, dt)

    def draw(self, shadow_rgb: tuple[int, int, int], alpha: float) -> None:
        pad = 34
        grow = self.state.hover * 9 - self.state.press * 5
        rect = self.rect.inflate(round(grow), round(grow * 0.6))
        p = Painter(rect.width + pad * 2, rect.height + pad * 2)
        body = pygame.Rect(pad, pad, rect.width, rect.height)
        draw_neumorphic_card(p, body, 24, bg_alpha=156 + round(self.state.hover * 28), shadow_rgb=shadow_rgb)
        if self.state.flash > 0:
            p.rounded(body.inflate(4, 4), (244, 114, 182, round(42 * self.state.flash)), body.height // 2 + 2)
        p.circle((255, 255, 255, 166), (body.x + 32, body.centery), 18)
        draw_pin_icon(p, (body.x + 32, body.centery + 1), COLORS["pink"])
        p.text(self.text, 20, COLORS["ink"], (body.x + 62, body.centery - 7), "midleft", True)
        p.text("当前位置", 11, COLORS["muted"], (body.x + 63, body.centery + 15), "midleft", True)
        draw_surface_gl(
            p.surface,
            rect.x - pad,
            rect.y - pad,
            p.logical_width,
            p.logical_height,
            alpha=alpha,
            scale=1.0 + self.state.hover * 0.035 - self.state.press * 0.06,
            z=10 * self.state.hover,
        )


class TimePill:
    def __init__(self) -> None:
        self.rect = pygame.Rect(324, 38, 196, 60)
        self.state = ButtonState()
        self.icon_bump = 0.0
        self.period = "morning"
        self.label = "第1天 早上"
        self.can_switch = False

    @property
    def current(self) -> dict:
        return TIME_STATES.get(self.period, TIME_STATES["morning"])

    def update(self, mouse: tuple[int, int], down: bool, dt: float, x: int, y: int, scene) -> None:
        gs = get_game_state()
        self.period = gs.game_time.get_period_name()
        self.label = gs.game_time.get_display_text()
        self.can_switch = bool(getattr(scene, "time_variants", None)) and len(scene.time_variants) > 1
        self.rect.x = x
        self.rect.y = y
        self.rect.width = max(190, min(282, text_width(self.label, 17, True) + 82))
        self.state.update(self.rect.collidepoint(mouse), down, dt)
        self.icon_bump = exp_smooth(self.icon_bump, 0.0, 18.0, dt)

    def contains(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)

    def click(self) -> None:
        self.state.click()
        self.icon_bump = 1.0

    def draw(self, shadow_rgb: tuple[int, int, int], alpha: float) -> None:
        pad = 34
        grow = self.state.hover * 8 - self.state.press * 5
        rect = self.rect.inflate(round(grow), round(grow * 0.5))
        st = self.current
        p = Painter(rect.width + pad * 2, rect.height + pad * 2)
        body = pygame.Rect(pad, pad, rect.width, rect.height)
        bg_alpha = 106 + round(self.state.hover * 32)
        if not self.can_switch:
            bg_alpha = 96 + round(self.state.hover * 18)
        draw_neumorphic_card(p, body, 24, bg_alpha=bg_alpha + 34, shadow_rgb=shadow_rgb)
        if self.state.flash > 0:
            p.rounded(body.inflate(4, 4), (*st["color"], round(50 * self.state.flash)), body.height // 2 + 2)
        text_color = COLORS["ink"] if self.can_switch else COLORS["muted"]
        icon_layer = Painter(38, 38)
        draw_time_icon(icon_layer, (19, 19), st["kind"], st["color"], st["fill"])
        icon_scale = 1.0 + self.icon_bump * 0.22
        icon_size = round(38 * TEXTURE_SCALE * icon_scale)
        p.surface.blit(
            pygame.transform.smoothscale(icon_layer.surface, (icon_size, icon_size)),
            (
                round((body.x + 18 - 19 * (icon_scale - 1)) * TEXTURE_SCALE),
                round((body.centery - 19 * icon_scale) * TEXTURE_SCALE),
            ),
        )
        p.text(self.label, 17, text_color, (body.x + 64, body.centery - 7), "midleft", True)
        p.text("点击切换时段" if self.can_switch else "当前时段", 10, st["color"], (body.x + 65, body.centery + 15), "midleft", True)
        draw_surface_gl(
            p.surface,
            rect.x - pad,
            rect.y - pad,
            p.logical_width,
            p.logical_height,
            alpha=alpha,
            scale=1.0 + self.state.hover * 0.035 - self.state.press * 0.06,
            z=10 * self.state.hover,
        )


class QuestDrawer:
    def __init__(self) -> None:
        self.open = False
        self.progress = 0.0
        self.state = ButtonState()
        self.ping = 0.0
        self.guidance: dict[str, str] | None = None

    def button_rect(self, height: int) -> pygame.Rect:
        y = height // 2 - 40
        x = round(-2 + 324 * self.progress)
        width = round(48 * (1.0 - 0.1 * self.progress))
        return pygame.Rect(x, y, width, 80)

    def has_content(self) -> bool:
        return bool(self.guidance)

    def update(self, mouse: tuple[int, int], down: bool, height: int, dt: float, guidance: dict[str, str] | None) -> None:
        self.guidance = guidance
        if not self.guidance:
            self.open = False
        rect = self.button_rect(height)
        self.state.update(self.has_content() and rect.collidepoint(mouse), down, dt)
        self.progress = exp_smooth(self.progress, 1.0 if self.open and self.guidance else 0.0, 10.0, dt)
        self.ping = (self.ping + dt / 1.5) % 1.0

    def contains(self, pos: tuple[int, int], height: int) -> bool:
        return self.has_content() and self.button_rect(height).collidepoint(pos)

    def click(self) -> None:
        if self.has_content():
            self.state.click()
            self.open = not self.open

    def draw(self, height: int, shadow_rgb: tuple[int, int, int], alpha: float) -> None:
        if not self.guidance and self.progress < 0.01:
            return

        panel_width = 334
        panel_height = 142
        panel_x = -panel_width - 32 + (panel_width + 42) * self.progress
        panel_y = height // 2 - panel_height // 2

        if self.progress > 0.01 and self.guidance:
            pad = 40
            p = Painter(panel_width + pad * 2, panel_height + pad * 2)
            body = pygame.Rect(pad, pad, panel_width, panel_height)
            draw_neumorphic_card(p, body, 24, bg_alpha=255, shadow_rgb=shadow_rgb)
            dot_center = (body.x + 33, body.y + 42)
            ring_radius = 7 + 12 * self.ping
            ring_alpha = round(115 * (1 - self.ping))
            p.circle((56, 189, 248, ring_alpha), dot_center, ring_radius, 2)
            p.circle(COLORS["sky"], dot_center, 10)
            p.circle((255, 255, 255, 215), (dot_center[0] - 2, dot_center[1] - 2), 3)

            status = self.guidance.get("status", "")
            title = self.guidance.get("title", "")
            hint = self.guidance.get("hint", "")
            title_text = f"{status}: {title}" if status else title
            title_lines = wrap_text(title_text, 15, panel_width - 78, True, max_lines=2)
            hint_lines = wrap_text(hint, 14, panel_width - 78, False, max_lines=2)

            y = body.y + 26
            for line in title_lines:
                p.text(line, 15, COLORS["ink"], (body.x + 60, y), "midleft", True)
                y += 22
            y += 3
            for line in hint_lines:
                p.text(line, 14, COLORS["muted"], (body.x + 60, y), "midleft")
                y += 21

            draw_surface_gl(p.surface, panel_x - pad, panel_y - pad, p.logical_width, p.logical_height, alpha=alpha * clamp(self.progress * 1.25, 0, 1))

        rect = self.button_rect(height)
        pad = 34
        hover_grow = self.state.hover * 5 - self.state.press * 2
        visual = rect.inflate(round(hover_grow), round(hover_grow))
        p = Painter(visual.width + pad * 2, visual.height + pad * 2)
        body = pygame.Rect(pad, pad, visual.width, visual.height)
        draw_neumorphic_card(p, body, 24, bg_alpha=255, shadow_rgb=shadow_rgb)
        draw_star_icon(p, (body.centerx, body.y + 28), COLORS["pink"])
        p.text("<" if self.open else ">", 20, COLORS["slate_400"], (body.centerx, body.y + 58), "center", True)
        draw_surface_gl(p.surface, visual.x - pad, visual.y - pad, p.logical_width, p.logical_height, alpha=alpha)


class ToolButton:
    def __init__(
        self,
        key: str,
        name: str,
        color: tuple[int, int, int],
        icon: Callable[[Painter, tuple[float, float], tuple[int, int, int]], None],
    ) -> None:
        self.key = key
        self.name = name
        self.color = color
        self.icon = icon
        self.center = pygame.Vector2(0, 0)
        self.width = 76
        self.height = 76
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.state = ButtonState()
        self.rot_x = 0.0
        self.rot_y = 0.0
        self.scale = 1.0
        self.idle_time = 0.0
        self.enabled = True

    def set_center(self, x: int, y: int) -> None:
        self.center.update(x, y)
        self.rect = pygame.Rect(
            round(x - self.width / 2),
            round(y - self.height / 2),
            self.width,
            self.height,
        )

    def contains(self, mouse: tuple[int, int]) -> bool:
        return self.rect.collidepoint(mouse)

    def update(self, mouse: tuple[int, int], down: bool, dt: float) -> None:
        self.idle_time += dt
        inside = self.contains(mouse)
        self.state.update(inside, down, dt)
        if inside:
            nx = ((mouse[0] - self.rect.x) / self.rect.width - 0.5) * 2
            ny = ((mouse[1] - self.rect.y) / self.rect.height - 0.5) * 2
            self.rot_x = exp_smooth(self.rot_x, -ny * 12, 18.0, dt)
            self.rot_y = exp_smooth(self.rot_y, nx * 12, 18.0, dt)
        else:
            self.rot_x = exp_smooth(self.rot_x, 0.0, 16.0, dt)
            self.rot_y = exp_smooth(self.rot_y, 0.0, 16.0, dt)
        target_scale = 0.95 if inside and down else (1.05 if inside else 1.0)
        self.scale += (target_scale - self.scale) * 0.2

    def click(self) -> None:
        self.state.click()

    def draw(self, shadow_rgb: tuple[int, int, int], alpha: float) -> None:
        pad = 46
        hover = self.state.hover
        bob = math.sin(self.idle_time * 2.1 + len(self.key)) * 1.4
        visual = self.rect.move(0, round(bob - hover * 4))

        p = Painter(visual.width + pad * 2, visual.height + pad * 2)
        body = pygame.Rect(pad, pad, visual.width, visual.height)
        base_alpha = 172 + round(26 * hover)
        if not self.enabled:
            base_alpha = 118 + round(20 * hover)
        draw_neumorphic_card(p, body, 22, bg_alpha=base_alpha, shadow_rgb=shadow_rgb)
        p.rounded(body.inflate(-8, -8), (255, 255, 255, 38), 18)
        if hover > 0.02 or self.state.flash > 0:
            p.rounded(body.inflate(6, 6), (*self.color, round(44 * hover + 72 * self.state.flash)), 25)
            p.circle((*self.color, round(42 * hover)), body.center, 33 + hover * 4)
        pulse = (math.sin(self.idle_time * 3.0 + len(self.name)) * 0.5 + 0.5) * (0.18 + hover * 0.4)
        p.circle((*self.color, round(28 * pulse)), body.center, 28 + pulse * 8, 1.4)

        icon_layer = Painter(58, 58)
        icon_color = self.color if self.enabled else COLORS["slate_400"]
        self.icon(icon_layer, (29, 29), icon_color)
        icon_scale = 1.0 + hover * 0.12 - self.state.press * 0.06
        icon_size = round(58 * TEXTURE_SCALE * icon_scale)
        p.surface.blit(
            pygame.transform.smoothscale(icon_layer.surface, (icon_size, icon_size)),
            (
                round((body.centerx - 29 * icon_scale) * TEXTURE_SCALE),
                round((body.centery - 29 * icon_scale - hover * 3) * TEXTURE_SCALE),
            ),
        )

        draw_surface_gl(
            p.surface,
            visual.x - pad,
            visual.y - pad,
            p.logical_width,
            p.logical_height,
            alpha=alpha,
            rot_x=self.rot_x,
            rot_y=self.rot_y,
            scale=self.scale,
            z=20 * hover,
        )

        if hover > 0.035:
            label_alpha = alpha * clamp(hover * 1.35, 0.0, 1.0)
            label_w = max(106, text_width(self.name, 15, True) + 34)
            label_h = 38
            label = Painter(label_w, label_h)
            label_rect = pygame.Rect(0, 0, label_w, label_h)
            draw_neumorphic_card(label, label_rect, 16, bg_alpha=172, shadow_rgb=shadow_rgb)
            label.text(self.name, 15, COLORS["ink"], (label_w // 2, label_h // 2), "center", True)
            label_x = self.rect.centerx - label_w / 2
            label_y = self.rect.bottom + 9 - (1 - hover) * 10
            draw_surface_gl(
                label.surface,
                label_x,
                label_y,
                label_w,
                label_h,
                alpha=label_alpha,
                scale=0.96 + hover * 0.04,
            )


class ExploreGlassHUD:
    """Interactive OpenGL overlay for ExploreScene."""

    def __init__(self) -> None:
        self.scene = ScenePill()
        self.time = TimePill()
        self.quest = QuestDrawer()
        self.tools = [
            ToolButton("rewind", "时间回溯", COLORS["purple"], draw_skeuo_hourglass),
            ToolButton("map", "地图", COLORS["green"], draw_skeuo_map),
            ToolButton("status", "角色档案", COLORS["blue"], draw_skeuo_profile),
        ]
        self.status_open = False
        self.status_progress = 0.0
        self.mouse_pos = (0, 0)
        self.mouse_down = False
        self._layout_tools(SCREEN_WIDTH)

    @property
    def shadow_rgb(self) -> tuple[int, int, int]:
        period = get_game_state().game_time.get_period_name()
        return TIME_STATES.get(period, TIME_STATES["morning"])["shadow"]

    def _layout_tools(self, width: int) -> None:
        gap = 14
        group_width = sum(tool.width for tool in self.tools) + gap * (len(self.tools) - 1)
        x = width - 32 - group_width
        y = 38
        for tool in self.tools:
            tool.set_center(x + tool.width // 2, y + tool.height // 2)
            x += tool.width + gap

    def update(self, dt: float, mouse_pos: tuple[int, int], mouse_down: bool, scene) -> None:
        self.mouse_pos = mouse_pos
        self.mouse_down = mouse_down

        self._layout_tools(SCREEN_WIDTH)
        self.time.update(mouse_pos, mouse_down, dt, 32, 38, scene)
        self.scene.rect.y = self.time.rect.bottom + 12
        self.scene.update(mouse_pos, mouse_down, getattr(scene, "title", ""), dt)
        self.quest.update(mouse_pos, mouse_down, SCREEN_HEIGHT, dt, getattr(scene.task_ui, "guidance", None))

        gs = get_game_state()
        self.tools[0].enabled = gs.game_time.can_rewind()
        for tool in self.tools:
            tool.update(mouse_pos, mouse_down, dt)

        self.status_progress = exp_smooth(self.status_progress, 1.0 if self.status_open else 0.0, 11.0, dt)

    def handle_event(self, event, scene) -> bool:
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        pos = event.pos
        if self.time.contains(pos) and self.time.can_switch:
            self.time.click()
            scene._switch_time_period()
            return True

        if self.quest.contains(pos, SCREEN_HEIGHT):
            self.quest.click()
            return True

        for tool in self.tools:
            if not tool.contains(pos):
                continue
            tool.click()
            if tool.key == "rewind":
                scene._trigger_rewind()
            elif tool.key == "map":
                scene.map_ui.toggle()
            elif tool.key == "status":
                self.status_open = not self.status_open
            return True

        if self.status_progress > 0.05 and self._status_rect().collidepoint(pos):
            return True

        return False

    def is_hovering(self) -> bool:
        if self.scene.rect.collidepoint(self.mouse_pos):
            return True
        if self.time.rect.collidepoint(self.mouse_pos):
            return True
        if self.quest.contains(self.mouse_pos, SCREEN_HEIGHT):
            return True
        if any(tool.contains(self.mouse_pos) for tool in self.tools):
            return True
        return self.status_progress > 0.05 and self._status_rect().collidepoint(self.mouse_pos)

    def draw_gl(self, scene, alpha: float = 1.0) -> None:
        if getattr(scene.map_ui, "visible", False):
            return

        self._configure_gl(SCREEN_WIDTH, SCREEN_HEIGHT)
        alpha = clamp(alpha, 0.0, 1.0)
        if alpha <= 0.01:
            return

        self._draw_hotspots(scene, alpha)
        self.scene.draw(self.shadow_rgb, alpha)
        self.time.draw(self.shadow_rgb, alpha)
        self.quest.draw(SCREEN_HEIGHT, self.shadow_rgb, alpha)
        self._draw_notifications(scene, alpha)
        self._draw_status_panel(alpha)
        for tool in self.tools:
            tool.draw(self.shadow_rgb, alpha)

    def _configure_gl(self, width: int, height: int) -> None:
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, width, height, 0, -1000, 1000)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glClear(GL_DEPTH_BUFFER_BIT)
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        try:
            glEnable(GL_MULTISAMPLE)
            glEnable(GL_LINE_SMOOTH)
            glEnable(GL_POLYGON_SMOOTH)
            glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
            glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
        except Exception:
            pass

    def _draw_hotspots(self, scene, alpha: float) -> None:
        hotspots = list(scene._iter_visible_hotspots())
        for hotspot in hotspots:
            self._draw_hotspot_marker(hotspot, getattr(scene, "game_time", 0.0), alpha)

        for hotspot in hotspots:
            if getattr(hotspot, "hover_progress", 0.0) > 0.06:
                self._draw_hotspot_card(hotspot, alpha)

    def _draw_hotspot_marker(self, hotspot, time_value: float, alpha: float) -> None:
        progress = clamp(getattr(hotspot, "hover_progress", 0.0), 0.0, 1.0)
        pulse = math.sin(time_value * 3.2 + len(getattr(hotspot, "id", ""))) * 0.5 + 0.5
        color = (251, 191, 36) if not getattr(hotspot, "discovered", False) else (52, 211, 153)
        if getattr(hotspot, "render_type", "dot") == "exclamation":
            color = (248, 113, 113)

        marker_size = 86
        pad = 46
        p = Painter(marker_size + pad * 2, marker_size + pad * 2)
        body_center = (pad + marker_size / 2, pad + marker_size / 2)
        if getattr(hotspot, "render_type", "dot") == "exclamation":
            draw_skeuo_exclamation_hotspot(p, body_center, progress, pulse)
        else:
            draw_skeuo_hotspot(p, body_center, color, progress, pulse)

        x, y = hotspot.dot_pos
        scale = 0.78 + pulse * 0.04 + progress * 0.26
        draw_surface_gl(
            p.surface,
            x - marker_size / 2 - pad,
            y - marker_size / 2 - pad - progress * 8,
            p.logical_width,
            p.logical_height,
            alpha=alpha * (0.78 + progress * 0.22),
            rot_x=-10 * progress,
            rot_y=12 * progress,
            scale=scale,
        )

    def _draw_hotspot_card(self, hotspot, alpha: float) -> None:
        progress = clamp(getattr(hotspot, "hover_progress", 0.0), 0.0, 1.0)
        title = getattr(hotspot, "title", "") or "互动点"
        desc = getattr(hotspot, "desc", "")
        title_w = text_width(title, 18, True)
        desc_lines = wrap_text(desc, 14, 300, False, max_lines=2)
        card_w = max(220, min(360, max(title_w + 44, 260)))
        card_h = 78 + len(desc_lines) * 20
        dot_x, dot_y = hotspot.dot_pos
        card_x = max(20, min(dot_x - card_w / 2, SCREEN_WIDTH - card_w - 20))
        card_y = max(18, dot_y - card_h - 74 - 16 * progress)

        pad = 34
        p = Painter(card_w + pad * 2, card_h + pad * 2)
        body = pygame.Rect(pad, pad, card_w, card_h)
        draw_neumorphic_card(p, body, 20, bg_alpha=188, shadow_rgb=self.shadow_rgb)
        p.circle((251, 191, 36, 190), (body.x + 25, body.y + 28), 8)
        p.text(title, 18, COLORS["ink"], (body.x + 44, body.y + 28), "midleft", True)
        y = body.y + 54
        if desc_lines:
            for line in desc_lines:
                p.text(line, 14, COLORS["muted"], (body.x + 22, y), "midleft")
                y += 20
        else:
            p.text("点击进行互动", 14, COLORS["muted"], (body.x + 22, y), "midleft")

        draw_surface_gl(
            p.surface,
            card_x - pad,
            card_y - pad,
            p.logical_width,
            p.logical_height,
            alpha=alpha * clamp(progress * 1.4, 0.0, 1.0),
            scale=0.94 + progress * 0.06,
        )

    def _status_rect(self) -> pygame.Rect:
        return pygame.Rect(SCREEN_WIDTH - 362, 132, 330, 232)

    def _draw_status_panel(self, alpha: float) -> None:
        if self.status_progress <= 0.01:
            return

        gs = get_game_state()
        stats = [
            ("智力", str(gs.get_player_stat("intelligence"))),
            ("体力", f"{gs.get_player_stat('stamina')}/100"),
            ("余额", str(gs.get_player_stat("money"))),
        ]
        npc_items = list(gs.npc_affections.items())
        height = 146 + len(npc_items) * 28
        height = max(190, min(360, height))
        rect = self._status_rect()
        rect.height = height
        slide = round((1 - self.status_progress) * 28)

        pad = 40
        p = Painter(rect.width + pad * 2, rect.height + pad * 2)
        body = pygame.Rect(pad, pad, rect.width, rect.height)
        draw_neumorphic_card(p, body, 24, bg_alpha=178, shadow_rgb=self.shadow_rgb)
        p.text("角色档案", 22, COLORS["pink"], (body.centerx, body.y + 36), "center", True)
        p.text("PROFILE", 11, COLORS["muted"], (body.centerx, body.y + 62), "center", True)

        y = body.y + 94
        for label, value in stats:
            p.text(label, 14, COLORS["muted"], (body.x + 24, y), "midleft", True)
            p.text(value, 15, COLORS["ink"], (body.right - 24, y), "midright", True)
            y += 28

        if npc_items:
            p.line((100, 116, 139, 70), (body.x + 20, y - 8), (body.right - 20, y - 8), 1)
            for npc_id, affection in npc_items[:6]:
                p.text(str(npc_id), 14, COLORS["muted"], (body.x + 24, y), "midleft", True)
                p.text(f"好感 {affection}", 14, COLORS["ink"], (body.right - 24, y), "midright", True)
                y += 28

        draw_surface_gl(
            p.surface,
            rect.x - pad + slide,
            rect.y - pad,
            p.logical_width,
            p.logical_height,
            alpha=alpha * clamp(self.status_progress * 1.2, 0, 1),
        )

    def _draw_notifications(self, scene, alpha: float) -> None:
        notifications = getattr(scene.task_ui, "notifications", [])
        if not notifications:
            return

        y = 222
        if self.status_progress > 0.04:
            y = max(y, self._status_rect().bottom + 18)

        for notification in notifications[:4]:
            height = self._draw_notification(notification, y, alpha)
            y += height + 10

    def _draw_notification(self, notification: dict, y: int, overlay_alpha: float) -> int:
        progress = notification.get("progress", 0.0)
        if progress < 0.2:
            local_alpha = progress / 0.2
            offset_x = int((1 - local_alpha) * 88)
        elif progress > 0.8:
            local_alpha = 1.0 - (progress - 0.8) / 0.2
            offset_x = int((1 - local_alpha) * 88)
        else:
            local_alpha = 1.0
            offset_x = 0

        message = notification.get("message", "")
        lines = wrap_text(message, 15, 328, False, max_lines=3)
        line_height = 22
        width = 382
        height = max(54, len(lines) * line_height + 24)
        x = SCREEN_WIDTH - width - 32 + offset_x

        pad = 28
        p = Painter(width + pad * 2, height + pad * 2)
        body = pygame.Rect(pad, pad, width, height)
        draw_neumorphic_card(p, body, 18, bg_alpha=178, shadow_rgb=self.shadow_rgb)
        for index, line in enumerate(lines):
            p.text(line, 15, COLORS["ink"], (body.x + 22, body.y + 19 + index * line_height), "midleft", True)

        draw_surface_gl(
            p.surface,
            x - pad,
            y - pad,
            p.logical_width,
            p.logical_height,
            alpha=overlay_alpha * clamp(local_alpha, 0, 1),
        )
        return height
