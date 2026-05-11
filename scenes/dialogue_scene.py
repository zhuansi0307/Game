"""
对话场景
显示对话内容，支持鼠标点击或空格推进对话
"""

import pygame
from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG_DARK, COLOR_TEXT, COLOR_CHAMPAGNE, COLOR_PANEL, COLOR_DIALOGUE_BG, COLOR_DIALOGUE_BORDER
from engine.scene_manager import BaseScene
from engine.ui import draw_text, draw_panel
from engine.dialogue import DialogueRunner


class DialogueScene(BaseScene):
    """对话场景"""

    def __init__(self, scene_manager, asset_manager):
        """
        初始化对话场景
        :param scene_manager: 场景管理器
        :param asset_manager: 资源管理器
        """
        super().__init__(scene_manager)
        self.asset_manager = asset_manager

        # 对话运行器
        self.dialogue_runner = DialogueRunner(asset_manager)

        # 当前对话ID和返回场景
        self.dialogue_id = None
        self.return_scene = None
        self.task_callback = None

        # 加载字体
        self.font_speaker = asset_manager.load_font(28)
        self.font_text = asset_manager.load_font(32)
        self.font_hint = asset_manager.load_font(18)

        # 对话框位置和尺寸
        self.box_x = 100
        self.box_y = SCREEN_HEIGHT - 240
        self.box_width = SCREEN_WIDTH - 200
        self.box_height = 180

        # 鼠标位置
        self.mouse_pos = (0, 0)

        # 点击区域（用于检测点击推进对话）
        self.click_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)

        # 文本动画
        self.text_progress = 1.0  # 0.0 - 1.0
        self.text_speed = 30  # 每秒显示字符数

        # 淡入效果
        self.fade_in = 0.0

        print("[对话场景] 初始化完成")

    def on_enter(self, **kwargs):
        """进入场景时调用"""
        self.dialogue_id = kwargs.get("dialogue_id")
        self.return_scene = kwargs.get("return_scene", "main_menu")
        self.task_callback = kwargs.get("task_callback")

        if not self.dialogue_id:
            print("[错误] 对话场景缺少 dialogue_id 参数")
            self.scene_manager.change_scene(self.return_scene)
            return

        # 开始对话
        if not self.dialogue_runner.start(self.dialogue_id):
            print(f"[错误] 无法加载对话: {self.dialogue_id}")
            self.scene_manager.change_scene(self.return_scene)
            return

        # 重置文本动画
        self.text_progress = 0.0
        self.fade_in = 0.0

        print(f"[对话场景] 开始对话: {self.dialogue_id}")

    def handle_event(self, event):
        """处理事件"""
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # 左键点击
                self._handle_click()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                self._handle_click()
            elif event.key == pygame.K_ESCAPE:
                # ESC 跳过对话并返回
                self._return_to_prev_scene()

        return True  # 阻止事件传播

    def _handle_click(self):
        """处理点击推进对话"""
        # 如果文本动画还没完成，立即显示完整文本
        if self.text_progress < 1.0:
            self.text_progress = 1.0
        else:
            # 推进到下一句
            if self.dialogue_runner.next():
                # 重置文本动画
                self.text_progress = 0.0
            else:
                # 对话结束，返回
                self._return_to_prev_scene()

    def _return_to_prev_scene(self):
        """返回上一个场景"""
        self.dialogue_runner.reset()
        if self.task_callback == "advance_task":
            self.scene_manager.change_scene(self.return_scene, task_callback="advance_task")
        else:
            self.scene_manager.change_scene(self.return_scene)

    def update(self, dt):
        """每帧更新"""
        # 淡入动画
        if self.fade_in < 1.0:
            self.fade_in += dt * 3
            if self.fade_in > 1.0:
                self.fade_in = 1.0

        # 更新文本动画
        if self.text_progress < 1.0:
            self.text_progress += dt * self.text_speed / 50  # 假设平均50字
            if self.text_progress > 1.0:
                self.text_progress = 1.0

    def draw(self, screen):
        """绘制场景"""
        # 获取当前对话行
        current_line = self.dialogue_runner.current_line()
        if not current_line:
            return

        # 绘制背景（半透明遮罩）
        self._draw_background(screen)

        # 绘制对话框
        self._draw_dialogue_box(screen, current_line)

        # 绘制进度指示器
        self._draw_progress(screen)

        # 绘制淡入效果
        if self.fade_in < 1.0:
            fade_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            fade_surface.fill(COLOR_BG_DARK)
            fade_surface.set_alpha(int(255 * (1 - self.fade_in)))
            screen.blit(fade_surface, (0, 0))

    def _draw_background(self, screen):
        """绘制背景（半透明遮罩让对话框更突出）"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 80))
        screen.blit(overlay, (0, 0))

    def _draw_dialogue_box(self, screen, line):
        """绘制对话框"""
        speaker = line.get("speaker", "")
        text = line.get("text", "")

        # 截取显示的字符数
        visible_chars = int(len(text) * self.text_progress)
        display_text = text[:visible_chars]

        # 绘制对话框背景
        box_surface = pygame.Surface((self.box_width, self.box_height), pygame.SRCALPHA)
        box_surface.fill((*COLOR_DIALOGUE_BG, 235))

        # 绘制香槟金边框
        pygame.draw.rect(box_surface, (*COLOR_DIALOGUE_BORDER, 255),
                        (0, 0, self.box_width, self.box_height), 2)

        # 绘制内部细线
        pygame.draw.rect(box_surface, (*COLOR_PANEL, 100),
                        (6, 6, self.box_width - 12, self.box_height - 12), 1)

        screen.blit(box_surface, (self.box_x, self.box_y))

        # 绘制说话者名称
        if speaker:
            speaker_surface = self.font_speaker.render(speaker, True, COLOR_CHAMPAGNE)
            screen.blit(speaker_surface, (self.box_x + 30, self.box_y + 20))

            # 名称下划线
            line_end_x = self.box_x + 30 + speaker_surface.get_width() + 10
            pygame.draw.line(screen, (*COLOR_CHAMPAGNE, 100),
                           (self.box_x + 30, self.box_y + 50),
                           (line_end_x, self.box_y + 50), 1)

        # 绘制对话内容
        text_x = self.box_x + 30
        text_y = self.box_y + 65
        text_max_width = self.box_width - 60

        # 支持自动换行
        self._draw_wrapped_text(screen, display_text, (text_x, text_y),
                               self.font_text, COLOR_TEXT, text_max_width)

        # 如果文本还没显示完，显示省略号
        if self.text_progress < 1.0:
            ellipsis_x = self.box_x + self.box_width - 50
            ellipsis_y = self.box_y + self.box_height - 40
            dots = "." * (int(pygame.time.get_ticks() / 500) % 4)
            dots_surface = self.font_hint.render(dots, True, (100, 105, 115))
            screen.blit(dots_surface, (ellipsis_x, ellipsis_y))

    def _draw_wrapped_text(self, screen, text, pos, font, color, max_width):
        """
        绘制自动换行的文本
        :param screen: pygame屏幕surface
        :param text: 文本内容
        :param pos: 起始位置 (x, y)
        :param font: 字体对象
        :param color: 文字颜色
        :param max_width: 最大宽度
        """
        words = text.split('\n')
        x, y = pos
        line_height = font.get_height() + 8

        for word in words:
            if word.strip() == '':
                y += line_height
                continue

            words_in_line = word.split()
            current_line = ""

            for w in words_in_line:
                test_line = current_line + " " + w if current_line else w
                if font.size(test_line)[0] <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        text_surface = font.render(current_line, True, color)
                        screen.blit(text_surface, (x, y))
                        y += line_height
                    current_line = w

            if current_line:
                text_surface = font.render(current_line, True, color)
                screen.blit(text_surface, (x, y))
                y += line_height

    def _draw_progress(self, screen):
        """绘制对话进度"""
        progress = self.dialogue_runner.get_progress()
        progress_text = f"{progress[0]}/{progress[1]}"

        progress_surface = self.font_hint.render(progress_text, True, (100, 105, 115))
        progress_rect = progress_surface.get_rect(
            bottomright=(self.box_x + self.box_width - 20, self.box_y + self.box_height - 15)
        )
        screen.blit(progress_surface, progress_rect)

        # 绘制提示文字
        hint_text = "点击或按空格继续 | ESC 跳过"
        hint_surface = self.font_hint.render(hint_text, True, (80, 85, 95))
        hint_rect = hint_surface.get_rect(
            midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 20)
        )
        screen.blit(hint_surface, hint_rect)
