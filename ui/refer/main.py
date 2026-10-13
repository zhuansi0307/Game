import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random

# --- 全局配置 ---
WIDTH, HEIGHT = 1024, 768
FPS = 60
# 尝试加载支持中文的系统字体
CHINESE_FONT = 'microsoftyahei' if pygame.font.match_font('microsoftyahei') else None

class Particle:
    def __init__(self):
        self.reset()
        self.y = random.uniform(0, HEIGHT) # 初始随机分布

    def reset(self):
        self.size = random.uniform(5, 20)
        self.x = random.uniform(0, WIDTH)
        self.y = HEIGHT + self.size
        self.speed = random.uniform(0.5, 2.0)
        self.alpha = random.uniform(0.3, 0.8)

    def update(self):
        self.y -= self.speed
        if self.y < -self.size:
            self.reset()

    def draw(self):
        glColor4f(1.0, 1.0, 1.0, self.alpha)
        glBegin(GL_QUADS)
        glVertex2f(self.x, self.y)
        glVertex2f(self.x + self.size, self.y)
        glVertex2f(self.x + self.size, self.y + self.size)
        glVertex2f(self.x, self.y + self.size)
        glEnd()

class InteractiveUIElement:
    def __init__(self, text, x, y, width, height, is_title=False):
        self.text = text
        self.rect = pygame.Rect(x - width//2, y - height//2, width, height)
        self.is_title = is_title

        # 交互变量
        self.target_rot_x = 0
        self.target_rot_y = 0
        self.current_rot_x = 0
        self.current_rot_y = 0
        self.target_scale = 1.0
        self.current_scale = 1.0
        self.is_hovered = False

        # 生成并绑定 OpenGL 纹理
        self.texture_id = self.create_texture()

    def create_texture(self):
        """用 Pygame 绘制高质量 2D UI，并转换为 OpenGL 纹理"""
        surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)

        # 1. 绘制半透明毛玻璃背景 (Glassmorphism 拟态)
        bg_alpha = 90 if self.is_title else 120
        pygame.draw.rect(surf, (255, 255, 255, bg_alpha), (0, 0, self.rect.width, self.rect.height), border_radius=24)
        # 绘制高亮边框
        pygame.draw.rect(surf, (255, 255, 255, 180), (0, 0, self.rect.width, self.rect.height), width=2, border_radius=24)

        # 2. 绘制文字
        if self.is_title:
            font = pygame.font.SysFont(CHINESE_FONT, 56, bold=True)
            text_color = (244, 114, 182) # 粉色调代替渐变
            sub_font = pygame.font.SysFont(None, 24, bold=True)

            text_surf = font.render(self.text, True, text_color)
            sub_surf = sub_font.render("SWEET GIRL PLAN", True, (100, 116, 139))

            surf.blit(text_surf, (self.rect.width//2 - text_surf.get_width()//2, 30))
            surf.blit(sub_surf, (self.rect.width//2 - sub_surf.get_width()//2, 100))
        else:
            font = pygame.font.SysFont(CHINESE_FONT, 28, bold=True)
            text_surf = font.render(self.text, True, (51, 65, 85))
            surf.blit(text_surf, (self.rect.width//2 - text_surf.get_width()//2, self.rect.height//2 - text_surf.get_height()//2))

        # 3. 将 Pygame Surface 转换为 OpenGL 纹理
        texture_data = pygame.image.tostring(surf, "RGBA", True) # True 表示翻转 Y 轴匹配 OpenGL
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.rect.width, self.rect.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)

        return tex_id

    def update(self, mx, my, mouse_pressed):
        """处理鼠标悬浮、偏转和点击逻辑"""
        self.is_hovered = self.rect.collidepoint(mx, my)

        if self.is_hovered:
            # 计算鼠标在元素内部的归一化坐标 (-1 到 1)
            # 等同于 JS 中的 css var(--x) 和 var(--y)
            norm_x = ((mx - self.rect.x) / self.rect.width - 0.5) * 2
            norm_y = ((my - self.rect.y) / self.rect.height - 0.5) * 2

            # 最大偏转角度 12 度
            self.target_rot_y = norm_x * 12.0
            self.target_rot_x = norm_y * -12.0

            self.target_scale = 0.95 if mouse_pressed else 1.05
        else:
            self.target_rot_x = 0
            self.target_rot_y = 0
            self.target_scale = 1.0

        # 平滑插值 (Lerp) 实现动画过渡效果
        self.current_rot_x += (self.target_rot_x - self.current_rot_x) * 0.15
        self.current_rot_y += (self.target_rot_y - self.current_rot_y) * 0.15
        self.current_scale += (self.target_scale - self.current_scale) * 0.2

    def draw(self):
        """使用 PyOpenGL 绘制带 3D 变换的纹理"""
        cx, cy = self.rect.centerx, self.rect.centery
        w, h = self.rect.width / 2, self.rect.height / 2

        glPushMatrix()

        # 1. 移动到 UI 元素的中心点
        glTranslatef(cx, cy, 0)

        # 2. 应用 3D 变换 (缩放和 XY 轴旋转)
        glScalef(self.current_scale, self.current_scale, 1.0)
        glRotatef(self.current_rot_x, 1, 0, 0) # Rotate X
        glRotatef(self.current_rot_y, 0, 1, 0) # Rotate Y

        # 为了明显的 3D 效果，鼠标悬浮时 Z 轴微微抬起
        if self.is_hovered:
            glTranslatef(0, 0, 20)

        # 3. 绑定纹理并绘制 Quad
        glColor4f(1, 1, 1, 1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glEnable(GL_TEXTURE_2D)

        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex3f(-w, -h, 0)
        glTexCoord2f(1, 1); glVertex3f(w, -h, 0)
        glTexCoord2f(1, 0); glVertex3f(w, h, 0)
        glTexCoord2f(0, 0); glVertex3f(-w, h, 0)
        glEnd()

        glDisable(GL_TEXTURE_2D)
        glPopMatrix()

def draw_background_gradient():
    """绘制氛围渐变背景"""
    glBegin(GL_QUADS)
    # 左上浅蓝 (var(--bg-top) = #e0f2fe)
    glColor3f(224/255, 242/255, 254/255); glVertex2f(0, 0)
    # 右上
    glColor3f(200/255, 235/255, 250/255); glVertex2f(WIDTH, 0)
    # 右下浅青 (var(--bg-bottom) = #f0fdfa)
    glColor3f(240/255, 253/255, 250/255); glVertex2f(WIDTH, HEIGHT)
    # 左下
    glColor3f(220/255, 245/255, 252/255); glVertex2f(0, HEIGHT)
    glEnd()

def main():
    pygame.init()
    # 启用 OpenGL 双缓冲模式
    pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("甜妹攻略计划 - PyOpenGL 重构版")
    clock = pygame.time.Clock()

    # --- OpenGL 初始化设置 ---
    glViewport(0, 0, WIDTH, HEIGHT)
    # 使用正交投影，匹配像素坐标系
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, WIDTH, HEIGHT, 0, -1000, 1000)
    glMatrixMode(GL_MODELVIEW)

    # 启用 Alpha 透明混合
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    # 启用深度测试以正确遮挡 3D 旋转部分
    glEnable(GL_DEPTH_TEST)

    # --- 实例化 UI 和粒子 ---
    particles = [Particle() for _ in range(25)]

    center_x = WIDTH // 2
    ui_elements = [
        InteractiveUIElement("甜妹攻略计划", center_x, 200, 380, 160, is_title=True),
        InteractiveUIElement("开始游戏", center_x, 380, 260, 60),
        InteractiveUIElement("新游戏", center_x, 460, 260, 60),
        InteractiveUIElement("继续游戏", center_x, 540, 260, 60),
        InteractiveUIElement("设 置", center_x, 620, 260, 60)
    ]

    running = True
    while running:
        mouse_pressed = False
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1: # 左键
                    mouse_pressed = True

        # 获取鼠标坐标和按压状态
        mx, my = pygame.mouse.get_pos()
        mouse_buttons = pygame.mouse.get_pressed()
        is_pressing = mouse_buttons[0]

        # 画面渲染清理
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # 1. 绘制背景层
        glDisable(GL_DEPTH_TEST) # 背景不需要深度
        draw_background_gradient()

        # 2. 绘制并更新粒子
        for p in particles:
            p.update()
            p.draw()
        glEnable(GL_DEPTH_TEST) # UI 需要深度测试

        # 3. 绘制并更新 UI 元素
        for ui in ui_elements:
            ui.update(mx, my, is_pressing)
            ui.draw()

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
