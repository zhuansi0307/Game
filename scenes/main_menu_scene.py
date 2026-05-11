"""
主菜单场景
游戏启动界面，包含标题和三个功能按钮
采用 OpenGL 3D UI 效果（基于 refer/main.py）
"""

import pygame
from pygame.locals import DOUBLEBUF, OPENGL
from OpenGL.GL import (
    glViewport, glMatrixMode, glLoadIdentity, glOrtho,
    glEnable, glDisable, glBlendFunc, glClear, glClearColor,
    glGenTextures, glBindTexture, glTexParameteri,
    glTexImage2D, glPushMatrix, glPopMatrix,
    glTranslatef, glScalef, glRotatef, glColor4f, glColor3f,
    glBegin, glEnd, glVertex2f, glVertex3f, glTexCoord2f,
    GL_PROJECTION, GL_MODELVIEW, GL_TEXTURE_2D,
    GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER, GL_LINEAR,
    GL_RGBA, GL_UNSIGNED_BYTE, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA,
    GL_BLEND, GL_DEPTH_TEST, GL_QUADS, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
)
from engine.save_manager import get_save_manager
from engine.game_state import get_game_state
from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS
from engine.scene_manager import BaseScene


# --- OpenGL 辅助类 ---

class _Particle:
    def __init__(self):
        self.reset()
        self.y = __import__('random').uniform(0, SCREEN_HEIGHT)

    def reset(self):
        r = __import__('random')
        self.size = r.uniform(5, 20)
        self.x = r.uniform(0, SCREEN_WIDTH)
        self.y = SCREEN_HEIGHT + self.size
        self.speed = r.uniform(0.5, 2.0)
        self.alpha = r.uniform(0.3, 0.8)

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


class _InteractiveUIElement:
    def __init__(self, text, x, y, width, height, is_title=False, action=None):
        self.text = text
        self.rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
        self.is_title = is_title
        self.action = action

        self.target_rot_x = 0.0
        self.target_rot_y = 0.0
        self.current_rot_x = 0.0
        self.current_rot_y = 0.0
        self.target_scale = 1.0
        self.current_scale = 1.0
        self.is_hovered = False

        self._texture_surf = None
        self.texture_id = 0

    def ensure_texture(self):
        """在 OpenGL 上下文可用时创建纹理"""
        if self.texture_id == 0 and self._texture_surf is None:
            self._texture_surf = self._create_surface()
            try:
                texture_data = pygame.image.tostring(self._texture_surf, "RGBA", True)
                tex_id = glGenTextures(1)
                if tex_id is None or (isinstance(tex_id, list) and len(tex_id) == 0):
                    return
                tex_id = int(tex_id[0]) if isinstance(tex_id, (list, tuple)) else int(tex_id)
                glBindTexture(GL_TEXTURE_2D, tex_id)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                # 关键：纹理需要 premultiplied alpha 或正确的 wrap 模式
                glTexParameteri(GL_TEXTURE_2D, 0x2802, 0x812F)  # GL_TEXTURE_WRAP_S = GL_CLAMP_TO_EDGE
                glTexParameteri(GL_TEXTURE_2D, 0x2803, 0x812F)  # GL_TEXTURE_WRAP_T = GL_CLAMP_TO_EDGE
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self._texture_surf.get_width(), self._texture_surf.get_height(), 0, GL_RGBA, GL_UNSIGNED_BYTE, texture_data)
                self.texture_id = tex_id
            except Exception:
                pass

    def _create_surface(self):
        # 创建带透明通道的表面，先用完全透明填充
        surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        bg_alpha = 90 if self.is_title else 120
        # 绘制半透明毛玻璃背景
        pygame.draw.rect(surf, (255, 255, 255, bg_alpha), (0, 0, self.rect.width, self.rect.height), border_radius=24)
        # 绘制高亮边框
        pygame.draw.rect(surf, (255, 255, 255, 180), (0, 0, self.rect.width, self.rect.height), width=2, border_radius=24)

        if self.is_title:
            # 标题字体根据面板高度自适应
            title_font_size = max(48, int(self.rect.height * 0.35))
            font = pygame.font.SysFont('microsoftyahei', title_font_size, bold=True)
            text_color = (244, 114, 182)
            sub_font = pygame.font.SysFont(None, max(20, int(self.rect.height * 0.12)), bold=True)
            text_surf = font.render(self.text, True, text_color)
            sub_surf = sub_font.render("SWEET GIRL RESCUE PLAN", True, (100, 116, 139))
            surf.blit(text_surf, (self.rect.width // 2 - text_surf.get_width() // 2, int(self.rect.height * 0.18)))
            surf.blit(sub_surf, (self.rect.width // 2 - sub_surf.get_width() // 2, int(self.rect.height * 0.62)))
        else:
            # 按钮字体根据面板高度自适应
            btn_font_size = max(32, int(self.rect.height * 0.45))
            font = pygame.font.SysFont('microsoftyahei', btn_font_size, bold=True)
            text_surf = font.render(self.text, True, (51, 65, 85))
            surf.blit(text_surf, (self.rect.width // 2 - text_surf.get_width() // 2, self.rect.height // 2 - text_surf.get_height() // 2))
        return surf

    def update(self, mx, my, mouse_pressed):
        self.is_hovered = self.rect.collidepoint(mx, my)
        if self.is_hovered:
            norm_x = ((mx - self.rect.x) / self.rect.width - 0.5) * 2
            norm_y = ((my - self.rect.y) / self.rect.height - 0.5) * 2
            self.target_rot_y = norm_x * 12.0
            self.target_rot_x = norm_y * -12.0
            self.target_scale = 0.95 if mouse_pressed else 1.05
        else:
            self.target_rot_x = 0.0
            self.target_rot_y = 0.0
            self.target_scale = 1.0

        self.current_rot_x += (self.target_rot_x - self.current_rot_x) * 0.15
        self.current_rot_y += (self.target_rot_y - self.current_rot_y) * 0.15
        self.current_scale += (self.target_scale - self.current_scale) * 0.2

    def draw(self):
        cx, cy = self.rect.centerx, self.rect.centery
        w, h = self.rect.width / 2, self.rect.height / 2

        glPushMatrix()
        glTranslatef(cx, cy, 0)
        glScalef(self.current_scale, self.current_scale, 1.0)
        glRotatef(self.current_rot_x, 1, 0, 0)
        glRotatef(self.current_rot_y, 0, 1, 0)
        if self.is_hovered:
            glTranslatef(0, 0, 20)

        # 关键：启用纹理 + 混合，实现透明效果
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(1, 1, 1, 1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex3f(-w, -h, 0)
        glTexCoord2f(1, 1); glVertex3f(w, -h, 0)
        glTexCoord2f(1, 0); glVertex3f(w, h, 0)
        glTexCoord2f(0, 0); glVertex3f(-w, h, 0)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glPopMatrix()


class MainMenuScene(BaseScene):
    """主菜单场景（OpenGL 3D UI 版）"""

    def __init__(self, scene_manager, asset_manager):
        super().__init__(scene_manager)
        self.asset_manager = asset_manager
        self.save_manager = get_save_manager()

        self.particles = [_Particle() for _ in range(25)]
        self.ui_elements = []
        self._build_ui()

        self.mouse_pos = (0, 0)
        self.is_pressing = False
        self.fade_in = 0.0
        self._gl_initialized = False

        print("[主菜单] 初始化完成（OpenGL 3D UI 版）")

    def _build_ui(self):
        """根据存档状态构建 UI 元素，垂直占满屏幕"""
        has_save = self.save_manager.has_any_save()
        center_x = SCREEN_WIDTH // 2

        # 布局参数
        title_width = 700
        title_height = 180
        button_width = 480
        button_height = 90
        button_spacing = 40
        title_button_gap = 60  # 标题和第一个按钮之间的间距

        if has_save:
            num_buttons = 4
        else:
            num_buttons = 3

        # 计算总内容高度，垂直居中
        # 总高度 = 标题 + 标题按钮间距 + 所有按钮 + 所有按钮间距
        total_content_height = title_height + title_button_gap + (num_buttons * button_height) + ((num_buttons - 1) * button_spacing)
        top_y = (SCREEN_HEIGHT - total_content_height) // 2

        # 标题位置
        title_y = top_y + title_height // 2

        # 第一个按钮的 y 位置
        first_button_y = top_y + title_height + title_button_gap + button_height // 2

        self.ui_elements = [
            _InteractiveUIElement("甜妹拯救计划", center_x, title_y, title_width, title_height, is_title=True),
        ]

        if has_save:
            self.ui_elements.extend([
                _InteractiveUIElement("继续游戏", center_x, first_button_y, button_width, button_height, action="continue_game"),
                _InteractiveUIElement("开始新游戏", center_x, first_button_y + (button_height + button_spacing), button_width, button_height, action="start_game"),
                _InteractiveUIElement("存 档", center_x, first_button_y + (button_height + button_spacing) * 2, button_width, button_height, action="save_menu"),
                _InteractiveUIElement("设 置", center_x, first_button_y + (button_height + button_spacing) * 3, button_width, button_height, action="settings"),
            ])
        else:
            self.ui_elements.extend([
                _InteractiveUIElement("启动游戏", center_x, first_button_y, button_width, button_height, action="start_game"),
                _InteractiveUIElement("存 档", center_x, first_button_y + (button_height + button_spacing), button_width, button_height, action="save_menu"),
                _InteractiveUIElement("设 置", center_x, first_button_y + (button_height + button_spacing) * 2, button_width, button_height, action="settings"),
            ])

    def _refresh_buttons(self):
        """刷新按钮配置，根据存档状态"""
        self._build_ui()

    # 标记使用原生 OpenGL 渲染
    use_native_gl = True

    def on_enter(self, **kwargs):
        """进入场景时调用"""
        self.fade_in = 0.0
        self._refresh_buttons()
        # 窗口已统一为 OpenGL 模式，只需重新初始化 GL 状态
        self._gl_initialized = False
        print("[主菜单] 进入主菜单")

    def on_leave(self):
        """离开场景时调用"""
        print("[主菜单] 离开主菜单")

    def handle_event(self, event):
        """处理事件"""
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._handle_click()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "quit"
        return False

    def _handle_click(self):
        """处理按钮点击"""
        for ui in self.ui_elements:
            if ui.is_hovered and ui.action:
                action = ui.action
                if action == "continue_game":
                    self._continue_game()
                elif action == "start_game":
                    self._start_new_game()
                elif action == "save_menu":
                    self.scene_manager.change_scene("save_menu")
                elif action == "settings":
                    self.scene_manager.change_scene("settings")
                break

    def _start_new_game(self):
        """开始新游戏"""
        self.save_manager.reset_for_new_game()
        gs = get_game_state()
        gs.set_flag("task_opening_completed")
        gs.set_flag("opening_video_played")
        gs.current_scene = "second_floor_hallway"
        self.scene_manager.change_scene(
            "cutscene",
            cutscene_id="opening_video",
            arrive_scene="second_floor_hallway",
        )

    def _continue_game(self):
        """继续游戏，加载最新存档"""
        if not self.save_manager.load_latest_game():
            self.scene_manager.change_scene("second_floor_hallway")
            return

        gs = get_game_state()
        saved_scene = gs.current_scene or "second_floor_hallway"
        if saved_scene == "main_menu":
            saved_scene = "second_floor_hallway"

        if self.scene_manager.change_scene(saved_scene):
            print(f"[主菜单] 继续游戏，场景: {saved_scene}")
        else:
            self.scene_manager.change_scene("second_floor_hallway")

    def update(self, dt):
        """每帧更新"""
        if self.fade_in < 1.0:
            self.fade_in += dt * 2
            if self.fade_in > 1.0:
                self.fade_in = 1.0

        mx, my = self.mouse_pos
        mouse_buttons = pygame.mouse.get_pressed()
        self.is_pressing = mouse_buttons[0]

        for p in self.particles:
            p.update()
        for ui in self.ui_elements:
            ui.update(mx, my, self.is_pressing)

    def draw(self, screen):
        """绘制场景（OpenGL 渲染）"""
        # 确保 OpenGL 上下文已初始化
        if not self._gl_initialized:
            self._init_gl()
            self._gl_initialized = True

        # 确保所有 UI 纹理已创建
        for ui in self.ui_elements:
            ui.ensure_texture()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # 背景层（无深度测试）
        glDisable(GL_DEPTH_TEST)
        self._draw_background_gradient()

        # 粒子
        for p in self.particles:
            p.draw()

        # UI 层（启用深度测试 + 混合）
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        for ui in self.ui_elements:
            ui.draw()
        glDisable(GL_BLEND)

        # 淡入遮罩
        if self.fade_in < 1.0:
            glDisable(GL_DEPTH_TEST)
            glEnable(GL_BLEND)
            alpha = 1.0 - self.fade_in
            glColor4f(0.0, 0.0, 0.0, alpha)
            glBegin(GL_QUADS)
            glVertex2f(0, 0)
            glVertex2f(SCREEN_WIDTH, 0)
            glVertex2f(SCREEN_WIDTH, SCREEN_HEIGHT)
            glVertex2f(0, SCREEN_HEIGHT)
            glEnd()
            glDisable(GL_BLEND)

    def _draw_background_gradient(self):
        """绘制氛围渐变背景"""
        glBegin(GL_QUADS)
        glColor3f(224 / 255, 242 / 255, 254 / 255)
        glVertex2f(0, 0)
        glColor3f(200 / 255, 235 / 255, 250 / 255)
        glVertex2f(SCREEN_WIDTH, 0)
        glColor3f(240 / 255, 253 / 255, 250 / 255)
        glVertex2f(SCREEN_WIDTH, SCREEN_HEIGHT)
        glColor3f(220 / 255, 245 / 255, 252 / 255)
        glVertex2f(0, SCREEN_HEIGHT)
        glEnd()

    def _init_gl(self):
        """初始化 OpenGL 状态"""
        glViewport(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, -1000, 1000)
        glMatrixMode(GL_MODELVIEW)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_DEPTH_TEST)
        glClearColor(0.0, 0.0, 0.0, 1.0)
