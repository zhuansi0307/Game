"""
OpenGL 渲染器
为 pygame 场景提供 OpenGL 离屏渲染支持，避免窗口闪烁
"""

import pygame
from OpenGL.GL import (
    glViewport, glMatrixMode, glLoadIdentity, glOrtho,
    glEnable, glDisable, glBlendFunc,
    glGenTextures, glBindTexture, glTexParameteri,
    glTexImage2D, glPushMatrix, glPopMatrix,
    glTranslatef, glScalef, glColor4f,
    glBegin, glEnd, glVertex2f, glTexCoord2f,
    GL_PROJECTION, GL_MODELVIEW, GL_TEXTURE_2D,
    GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER, GL_LINEAR,
    GL_RGBA, GL_UNSIGNED_BYTE, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA,
    GL_BLEND, GL_QUADS, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    glClear, glClearColor,
)
from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT


class GLRenderer:
    """OpenGL 渲染器，用于将 pygame Surface 绘制到 OpenGL 窗口"""

    def __init__(self):
        self._texture_id = None
        self._initialized = False

    def init(self):
        """初始化 OpenGL 状态（在主菜单 init_gl 之后调用）"""
        if self._initialized:
            return
        self._texture_id = glGenTextures(1)
        if isinstance(self._texture_id, (list, tuple)):
            self._texture_id = int(self._texture_id[0])
        else:
            self._texture_id = int(self._texture_id)
        glBindTexture(GL_TEXTURE_2D, self._texture_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        self._initialized = True

    def render_pygame_surface(self, surface):
        """
        将 pygame Surface 渲染到当前 OpenGL 窗口
        :param surface: pygame Surface，尺寸应为 SCREEN_WIDTH x SCREEN_HEIGHT
        """
        if not self._initialized:
            self.init()

        # 确保 surface 是 RGBA 格式
        if surface.get_bitsize() != 32:
            surface = surface.convert_alpha()

        # 更新纹理
        texture_data = pygame.image.tostring(surface, "RGBA", True)
        glBindTexture(GL_TEXTURE_2D, self._texture_id)
        glTexImage2D(
            GL_TEXTURE_2D, 0, GL_RGBA,
            surface.get_width(), surface.get_height(),
            0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data
        )

        # 设置正交投影
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        # 禁用深度测试，启用混合
        glDisable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glColor4f(1.0, 1.0, 1.0, 1.0)

        # 绘制全屏四边形
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex2f(0, 0)
        glTexCoord2f(1, 1); glVertex2f(w, 0)
        glTexCoord2f(1, 0); glVertex2f(w, h)
        glTexCoord2f(0, 0); glVertex2f(0, h)
        glEnd()

        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)

        # 恢复矩阵
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def cleanup(self):
        """清理资源"""
        self._initialized = False
        self._texture_id = None
