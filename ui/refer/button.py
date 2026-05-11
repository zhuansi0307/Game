# -*- coding: utf-8 -*-
import math
import sys
from dataclasses import dataclass
from typing import Callable

import pygame
from pygame.locals import DOUBLEBUF, KEYDOWN, K_ESCAPE, MOUSEBUTTONDOWN, OPENGL, QUIT, RESIZABLE, VIDEORESIZE
from OpenGL.GL import *


WIDTH, HEIGHT = 1184, 744
FPS = 60
TEXTURE_SCALE = 2


COLORS = {
    "bg": (250, 250, 249),
    "ink": (51, 65, 85),
    "slate_400": (148, 163, 184),
    "slate_500": (100, 116, 139),
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
}


TIME_STATES = [
    {
        "label": "上午",
        "kind": "sun",
        "color": (251, 191, 36),
        "fill": (253, 230, 138),
        "shadow": (56, 189, 248),
    },
    {
        "label": "中午",
        "kind": "sun",
        "color": (249, 115, 22),
        "fill": (254, 215, 170),
        "shadow": (249, 115, 22),
    },
    {
        "label": "下午",
        "kind": "sunset",
        "color": (251, 113, 133),
        "fill": (254, 205, 211),
        "shadow": (244, 63, 94),
    },
    {
        "label": "晚上",
        "kind": "moon",
        "color": (129, 140, 248),
        "fill": (199, 210, 254),
        "shadow": (99, 102, 241),
    },
]


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
        image = font.render(text, True, color)
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


def upload_texture(surface: pygame.Surface) -> int:
    texture = glGenTextures(1)
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
    texture = upload_texture(surface)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture)
    glColor4f(1.0, 1.0, 1.0, alpha)

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
    glDeleteTextures([texture])


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

    def update(self, inside: bool, mouse_down: bool, clicked: bool, dt: float) -> bool:
        self.hover = exp_smooth(self.hover, 1.0 if inside else 0.0, 18.0, dt)
        self.press = exp_smooth(self.press, 1.0 if inside and mouse_down else 0.0, 24.0, dt)
        self.flash = max(0.0, self.flash - dt * 3.5)
        if inside and clicked:
            self.flash = 1.0
            return True
        return False


class ScenePill:
    def __init__(self) -> None:
        self.rect = pygame.Rect(32, 32, 190, 52)
        self.state = ButtonState()

    def update(self, mouse: tuple[int, int], down: bool, clicked: bool, dt: float) -> bool:
        return self.state.update(self.rect.collidepoint(mouse), down, clicked, dt)

    def draw(self, shadow_rgb: tuple[int, int, int]) -> None:
        pad = 34
        grow = self.state.hover * 7 - self.state.press * 4
        rect = self.rect.inflate(round(grow), round(grow * 0.6))
        p = Painter(rect.width + pad * 2, rect.height + pad * 2)
        body = pygame.Rect(pad, pad, rect.width, rect.height)
        draw_glass(p, body, body.height // 2, shadow_rgb, bg_alpha=122 + round(self.state.hover * 28))
        if self.state.flash > 0:
            p.rounded(body.inflate(4, 4), (*COLORS["sky"], round(48 * self.state.flash)), body.height // 2 + 2)
        p.circle((255, 255, 255, 130), (body.x + 32, body.centery), 17)
        draw_pin_icon(p, (body.x + 32, body.centery), COLORS["sky"])
        p.text("星空展望台", 18, COLORS["ink"], (body.x + 58, body.centery), "midleft", True)
        draw_surface_gl(p.surface, rect.x - pad, rect.y - pad, p.logical_width, p.logical_height)


class TimePill:
    def __init__(self) -> None:
        self.rect = pygame.Rect(238, 32, 118, 52)
        self.state = ButtonState()
        self.index = 2
        self.icon_bump = 0.0

    @property
    def current(self) -> dict:
        return TIME_STATES[self.index]

    def update(self, mouse: tuple[int, int], down: bool, clicked: bool, dt: float) -> bool:
        activated = self.state.update(self.rect.collidepoint(mouse), down, clicked, dt)
        if activated:
            self.index = (self.index + 1) % len(TIME_STATES)
            self.icon_bump = 1.0
        self.icon_bump = exp_smooth(self.icon_bump, 0.0, 18.0, dt)
        return activated

    def draw(self, shadow_rgb: tuple[int, int, int]) -> None:
        pad = 34
        grow = self.state.hover * 6 - self.state.press * 4
        rect = self.rect.inflate(round(grow), round(grow * 0.5))
        st = self.current
        p = Painter(rect.width + pad * 2, rect.height + pad * 2)
        body = pygame.Rect(pad, pad, rect.width, rect.height)
        draw_glass(p, body, body.height // 2, shadow_rgb, bg_alpha=125 + round(self.state.hover * 30))
        if self.state.flash > 0:
            p.rounded(body.inflate(4, 4), (*st["color"], round(50 * self.state.flash)), body.height // 2 + 2)
        icon_scale = 1.0 + self.icon_bump * 0.25
        icon_layer = Painter(38, 38)
        draw_time_icon(icon_layer, (19, 19), st["kind"], st["color"], st["fill"])
        icon_size = round(38 * TEXTURE_SCALE * icon_scale)
        p.surface.blit(
            pygame.transform.smoothscale(icon_layer.surface, (icon_size, icon_size)),
            (
                round((body.x + 19 - 19 * icon_scale) * TEXTURE_SCALE),
                round((body.centery - 19 * icon_scale) * TEXTURE_SCALE),
            ),
        )
        p.text(st["label"], 18, COLORS["ink"], (body.x + 70, body.centery), "center", True)
        draw_surface_gl(p.surface, rect.x - pad, rect.y - pad, p.logical_width, p.logical_height)


class QuestDrawer:
    def __init__(self) -> None:
        self.open = False
        self.progress = 0.0
        self.state = ButtonState()
        self.ping = 0.0

    def button_rect(self, height: int) -> pygame.Rect:
        y = height // 2 - 40
        x = round(-2 + 270 * self.progress)
        width = round(48 * (1.0 - 0.1 * self.progress))
        return pygame.Rect(x, y, width, 80)

    def update(self, mouse: tuple[int, int], down: bool, clicked: bool, height: int, dt: float) -> bool:
        rect = self.button_rect(height)
        inside = rect.collidepoint(mouse)
        if self.state.update(inside, down, clicked, dt):
            self.open = not self.open
        self.progress = exp_smooth(self.progress, 1.0 if self.open else 0.0, 10.0, dt)
        self.ping = (self.ping + dt / 1.5) % 1.0
        return inside

    def draw(self, height: int, shadow_rgb: tuple[int, int, int]) -> None:
        panel_width = 280
        panel_height = 118
        panel_x = -panel_width - 32 + (panel_width + 40) * self.progress
        panel_y = height // 2 - panel_height // 2

        if self.progress > 0.01:
            pad = 40
            p = Painter(panel_width + pad * 2, panel_height + pad * 2)
            body = pygame.Rect(pad, pad, panel_width, panel_height)
            draw_glass(p, body, 24, shadow_rgb, bg_alpha=118 + round(self.progress * 32), shadow_strength=46)
            dot_center = (body.x + 33, body.y + 42)
            ring_radius = 7 + 12 * self.ping
            ring_alpha = round(115 * (1 - self.ping))
            p.circle((56, 189, 248, ring_alpha), dot_center, ring_radius, 2)
            p.circle(COLORS["sky"], dot_center, 10)
            p.circle((255, 255, 255, 215), (dot_center[0] - 2, dot_center[1] - 2), 3)
            p.text("前往星空展望台，", 15, COLORS["ink"], (body.x + 60, body.y + 35), "midleft", True)
            p.text("赴约周末的流星雨观测。", 15, COLORS["ink"], (body.x + 60, body.y + 61), "midleft", True)
            draw_surface_gl(p.surface, panel_x - pad, panel_y - pad, p.logical_width, p.logical_height, alpha=clamp(self.progress * 1.25, 0, 1))

        rect = self.button_rect(height)
        pad = 34
        hover_grow = self.state.hover * 5 - self.state.press * 2
        visual = rect.inflate(round(hover_grow), round(hover_grow))
        p = Painter(visual.width + pad * 2, visual.height + pad * 2)
        body = pygame.Rect(pad, pad, visual.width, visual.height)
        radius = 24 if self.progress > 0.5 else 0
        draw_glass(p, body, 24, shadow_rgb, bg_alpha=126 + round(self.state.hover * 38), shadow_strength=40)
        draw_star_icon(p, (body.centerx, body.y + 28), COLORS["pink"])
        p.text("‹" if self.open else "›", 20, COLORS["slate_400"], (body.centerx, body.y + 58), "center", True)
        draw_surface_gl(p.surface, visual.x - pad, visual.y - pad, p.logical_width, p.logical_height)


class ToolButton:
    def __init__(
        self,
        name: str,
        color: tuple[int, int, int],
        icon: Callable[[Painter, tuple[float, float], tuple[int, int, int]], None],
    ) -> None:
        self.name = name
        self.color = color
        self.icon = icon
        self.center = pygame.Vector2(0, 0)
        self.radius = 32
        self.state = ButtonState()
        self.rot_x = 0.0
        self.rot_y = 0.0

    def set_center(self, x: int, y: int) -> None:
        self.center.update(x, y)

    def contains(self, mouse: tuple[int, int]) -> bool:
        return self.center.distance_to(mouse) <= self.radius

    def update(self, mouse: tuple[int, int], down: bool, clicked: bool, dt: float) -> bool:
        inside = self.contains(mouse)
        activated = self.state.update(inside, down, clicked, dt)
        if inside:
            nx = (mouse[0] - self.center.x) / self.radius
            ny = (mouse[1] - self.center.y) / self.radius
            self.rot_x = exp_smooth(self.rot_x, -ny * 20, 18.0, dt)
            self.rot_y = exp_smooth(self.rot_y, nx * 20, 18.0, dt)
        else:
            self.rot_x = exp_smooth(self.rot_x, 0.0, 16.0, dt)
            self.rot_y = exp_smooth(self.rot_y, 0.0, 16.0, dt)
        return activated

    def draw(self, shadow_rgb: tuple[int, int, int]) -> None:
        pad = 40
        size = 64
        p = Painter(size + pad * 2, size + pad * 2)
        body = pygame.Rect(pad, pad, size, size)
        draw_glass(p, body, 32, shadow_rgb, bg_alpha=118 + round(self.state.hover * 44), shadow_strength=38)
        if self.state.hover > 0.02 or self.state.flash > 0:
            p.circle((*self.color, round(self.state.hover * 38 + self.state.flash * 64)), body.center, 39)
        icon_layer = Painter(42, 42)
        self.icon(icon_layer, (21, 21), self.color)
        icon_scale = 1.0 + self.state.hover * 0.1 - self.state.press * 0.05
        p.surface.blit(
            pygame.transform.smoothscale(icon_layer.surface, (round(42 * TEXTURE_SCALE * icon_scale), round(42 * TEXTURE_SCALE * icon_scale))),
            (
                round((body.centerx - 21 * icon_scale) * TEXTURE_SCALE),
                round((body.centery - 21 * icon_scale - self.state.hover * 2) * TEXTURE_SCALE),
            ),
        )
        scale = 1.0 + self.state.hover * 0.05 - self.state.press * 0.1
        draw_surface_gl(
            p.surface,
            self.center.x - size / 2 - pad,
            self.center.y - size / 2 - pad,
            p.logical_width,
            p.logical_height,
            rot_x=self.rot_x,
            rot_y=self.rot_y,
            scale=scale,
        )

        if self.state.hover > 0.04:
            tooltip_alpha = clamp(self.state.hover * 1.25, 0.0, 1.0)
            text_width = max(84, len(self.name) * 16)
            tooltip = Painter(text_width, 34)
            rect = pygame.Rect(0, 0, text_width, 34)
            draw_glass(tooltip, rect, 14, shadow_rgb, bg_alpha=178, shadow_strength=20)
            tooltip.text(self.name, 13, COLORS["ink"], (text_width // 2, 17), "center", True)
            draw_surface_gl(
                tooltip.surface,
                self.center.x - text_width / 2,
                self.center.y + 42 - 10 * (1 - tooltip_alpha),
                text_width,
                34,
                alpha=tooltip_alpha,
            )


class HUDApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()
        self._setup_window(WIDTH, HEIGHT)
        pygame.display.set_caption("甜妹攻略计划 - PyOpenGL HUD")
        self.clock = pygame.time.Clock()

        self.scene = ScenePill()
        self.time = TimePill()
        self.quest = QuestDrawer()
        self.tools = [
            ToolButton("时间回溯", COLORS["purple"], draw_tool_hourglass),
            ToolButton("校园地图", COLORS["green"], draw_tool_map),
            ToolButton("角色档案", COLORS["blue"], draw_tool_user),
        ]
        self.cursor_hand = False
        self._layout_tools()

    @property
    def shadow_rgb(self) -> tuple[int, int, int]:
        return self.time.current["shadow"]

    def _setup_window(self, width: int, height: int) -> None:
        pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)
        pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
        try:
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 8)
        except pygame.error:
            pass
        try:
            pygame.display.set_mode((width, height), OPENGL | DOUBLEBUF | RESIZABLE, vsync=1)
        except TypeError:
            pygame.display.set_mode((width, height), OPENGL | DOUBLEBUF | RESIZABLE)
        self._configure_gl(width, height)

    def _configure_gl(self, width: int, height: int) -> None:
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, width, height, 0, -1000, 1000)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        try:
            glEnable(GL_MULTISAMPLE)
        except Exception:
            pass

    def _layout_tools(self) -> None:
        width = pygame.display.get_surface().get_width()
        group_width = 64 * 3 + 20 * 2
        start_x = width - 32 - group_width + 32
        y = 64
        for index, tool in enumerate(self.tools):
            tool.set_center(start_x + index * 84, y)

    def _set_cursor(self, hand: bool) -> None:
        if hand == self.cursor_hand:
            return
        self.cursor_hand = hand
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if hand else pygame.SYSTEM_CURSOR_ARROW)

    def run(self) -> None:
        running = True
        while running:
            dt = min(self.clock.tick(FPS) / 1000.0, 1 / 30)
            mouse = pygame.mouse.get_pos()
            mouse_down = pygame.mouse.get_pressed(num_buttons=3)[0]
            clicked = False

            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
                elif event.type == KEYDOWN and event.key == K_ESCAPE:
                    running = False
                elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                    clicked = True
                elif event.type == VIDEORESIZE:
                    new_w = max(760, event.w)
                    new_h = max(480, event.h)
                    self._setup_window(new_w, new_h)
                    self._layout_tools()

            hovering = False
            self.scene.update(mouse, mouse_down, clicked, dt)
            hovering = hovering or self.scene.rect.collidepoint(mouse)

            self.time.update(mouse, mouse_down, clicked, dt)
            hovering = hovering or self.time.rect.collidepoint(mouse)

            height = pygame.display.get_surface().get_height()
            hovering = self.quest.update(mouse, mouse_down, clicked, height, dt) or hovering

            for tool in self.tools:
                tool.update(mouse, mouse_down, clicked, dt)
                hovering = hovering or tool.contains(mouse)

            self._set_cursor(hovering)
            self.draw()

        pygame.quit()
        sys.exit()

    def draw(self) -> None:
        width, height = pygame.display.get_surface().get_size()
        glClearColor(COLORS["bg"][0] / 255, COLORS["bg"][1] / 255, COLORS["bg"][2] / 255, 0.0)
        glClear(GL_COLOR_BUFFER_BIT)
        glLoadIdentity()

        self.scene.draw(self.shadow_rgb)
        self.time.draw(self.shadow_rgb)
        self.quest.draw(height, self.shadow_rgb)
        for tool in self.tools:
            tool.draw(self.shadow_rgb)

        pygame.display.flip()


def main() -> None:
    HUDApp().run()


if __name__ == "__main__":
    main()
