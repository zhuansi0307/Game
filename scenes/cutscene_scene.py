"""
过场动画场景
显示过场动画内容，支持进度条和播放控制
"""

import pygame
from engine.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG_DARK,
    COLOR_TEXT, COLOR_CHAMPAGNE, COLOR_PANEL, COLOR_PANEL_BORDER
)
from engine.scene_manager import BaseScene
from engine.cutscene_player import CutscenePlayer, PlaybackState
from engine.audio_manager import get_audio_manager
from engine.ui import draw_text, draw_panel


class CutsceneScene(BaseScene):
    """过场动画场景"""

    def __init__(self, scene_manager, asset_manager):
        super().__init__(scene_manager)
        self.asset_manager = asset_manager

        self.player = CutscenePlayer(asset_manager)
        self.audio_manager = get_audio_manager()
        self.cutscenes_by_id = {
            cutscene.get("id"): cutscene
            for cutscene in asset_manager.load_cutscenes().get("cutscenes", [])
            if cutscene.get("id")
        }
        self.cutscene_id = None
        self.return_scene = None
        self.arrive_scene = None
        self.callback_on_complete = None
        self.completed = False

        self.fonts = {
            'title': asset_manager.load_font(36),
            'speaker': asset_manager.load_font(28),
            'dialogue': asset_manager.load_font(32),
            'time': asset_manager.load_font(20),
            'hint': asset_manager.load_font(18)
        }

        self.mouse_pos = (0, 0)
        self.fade_in = 0.0

        self.control_panel_height = 100
        self.dialogue_box_height = 160
        self.dialogue_box_y = SCREEN_HEIGHT - self.control_panel_height - self.dialogue_box_height - 20

        self.play_button_size = 50
        self.progress_bar_y = SCREEN_HEIGHT - 60
        self.progress_bar_height = 20

        self.control_buttons = []
        self.is_hovering_play = False
        self.show_controls = False
        self.controls_hide_timer = 0.0
        self.controls_timeout = 3.0

        print("[过场动画场景] 初始化完成")

    def on_enter(self, **kwargs):
        """进入场景时调用"""
        self.cutscene_id = kwargs.get("cutscene_id")
        self.return_scene = kwargs.get("return_scene", "main_menu")
        self.arrive_scene = kwargs.get("arrive_scene")
        self.callback_on_complete = kwargs.get("callback")
        self.completed = False

        if not self.cutscene_id:
            print("[错误] 过场动画场景缺少 cutscene_id 参数")
            self.scene_manager.change_scene(self.return_scene)
            return

        if self._play_audio_only_cutscene():
            self._on_cutscene_complete()
            return

        if not self.player.start_cutscene(self.cutscene_id):
            print(f"[错误] 无法播放过场动画: {self.cutscene_id}")
            self.cutscene_id = None

        self.fade_in = 0.0
        self.player.is_dragging = False
        self.show_controls = False
        self.controls_hide_timer = 0.0

        print(f"[过场动画场景] 播放: {self.cutscene_id}")

    def _play_audio_only_cutscene(self):
        cutscene = self.cutscenes_by_id.get(self.cutscene_id)
        if not cutscene:
            return False

        audio_path = cutscene.get("audio")
        if not audio_path or cutscene.get("video"):
            return False

        self.audio_manager.play_asset(self.asset_manager, audio_path)
        return True

    def handle_event(self, event):
        """处理事件"""
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            self._update_hover_state()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                controls_were_visible = self.show_controls
                self.show_controls = True
                self.controls_hide_timer = 0.0
                
                if controls_were_visible and self.player.handle_event(event, self.mouse_pos):
                    return True
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                if self.player.handle_event(event, self.mouse_pos):
                    return True

        elif event.type == pygame.KEYDOWN:
            self.show_controls = True
            self.controls_hide_timer = 0.0
            
            if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                if self.player.last_error:
                    self._skip_to_end()
                else:
                    self.player.toggle_play_pause()
            elif event.key == pygame.K_ESCAPE:
                self._skip_to_end()
            elif event.key == pygame.K_LEFT:
                self._seek_backward()
            elif event.key == pygame.K_RIGHT:
                self._seek_forward()

        if event.type == pygame.MOUSEMOTION and self.player.handle_event(event, self.mouse_pos):
            return True

        return False

    def _handle_click(self, pos):
        """处理点击"""
        if self.player.play_button_rect and self.player.play_button_rect.collidepoint(pos):
            self.player.toggle_play_pause()
        elif self.player.progress_bar_rect and self.player.progress_bar_rect.collidepoint(pos):
            progress = self._get_progress_from_position(pos[0])
            self.player.seek_to_progress(progress)

    def _update_hover_state(self):
        """更新悬停状态"""
        if self.player.play_button_rect:
            self.is_hovering_play = self.player.play_button_rect.collidepoint(self.mouse_pos)
        else:
            self.is_hovering_play = False

    def _get_progress_from_position(self, x):
        """根据x坐标计算进度"""
        if self.player.progress_bar_rect:
            bar_x = self.player.progress_bar_rect.left
            bar_width = self.player.progress_bar_rect.width
            progress = (x - bar_x) / bar_width
            return max(0.0, min(1.0, progress))
        return 0.0

    def _seek_backward(self):
        """快退10秒"""
        if self.player.current_cutscene:
            self.player.seek_to(self.player.current_time - 10)

    def _seek_forward(self):
        """快进10秒"""
        if self.player.current_cutscene:
            self.player.seek_to(self.player.current_time + 10)

    def _skip_to_end(self):
        """跳转到结尾"""
        if self.player.current_cutscene:
            self.player.finish()

    def update(self, dt):
        """每帧更新"""
        if self.fade_in < 1.0:
            self.fade_in += dt * 10
            if self.fade_in > 1.0:
                self.fade_in = 1.0

        self.player.update(dt)

        if self.player.playback_state == PlaybackState.PAUSED:
            self.show_controls = True
            self.controls_hide_timer = 0.0
        elif self.show_controls:
            self.controls_hide_timer += dt
            if (
                self.controls_hide_timer >= self.controls_timeout
                and self.player.playback_state == PlaybackState.PLAYING
                and not self.player.is_dragging
            ):
                self.show_controls = False

        if self.player.is_finished():
            self._on_cutscene_complete()

    def _on_cutscene_complete(self):
        """动画播放完成的回调"""
        if self.completed:
            return
        self.completed = True

        print(f"[过场动画场景] 播放完成: {self.cutscene_id}")

        if self.callback_on_complete and callable(self.callback_on_complete):
            self.callback_on_complete()

        self.player.reset()
        destination = self.arrive_scene if self.arrive_scene else self.return_scene
        if self.callback_on_complete == "advance_task":
            self.scene_manager.change_scene(destination, task_callback="advance_task")
        else:
            self.scene_manager.change_scene(destination)

    def draw(self, screen):
        """绘制场景"""
        self._draw_background(screen)
        self._draw_current_frame(screen)
        self._draw_control_panel(screen)
        self._draw_buffering_hint(screen)
        self._draw_fade_overlay(screen)

    def _draw_background(self, screen):
        """绘制背景"""
        screen.fill(COLOR_BG_DARK)

    def _draw_current_frame(self, screen):
        """绘制当前帧"""
        frame_image = self.player.get_current_frame()
        if frame_image:
            # Optimize: Only scale if the frame size doesn't match the screen size to save an expensive operation per frame
            if frame_image.get_size() != (SCREEN_WIDTH, SCREEN_HEIGHT):
                frame_to_draw = pygame.transform.smoothscale(frame_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
            else:
                frame_to_draw = frame_image
            screen.blit(frame_to_draw, (0, 0))

    def _draw_dialogue_box(self, screen):
        """绘制对话框"""
        dialogue = self.player.get_current_dialogue()
        if not dialogue:
            return

        box_rect = (50, self.dialogue_box_y, SCREEN_WIDTH - 100, self.dialogue_box_height)
        draw_panel(screen, box_rect, alpha=180)

        speaker = dialogue.get("speaker", "")
        text = dialogue.get("text", "")

        speaker_rect = (70, self.dialogue_box_y + 15, SCREEN_WIDTH - 140, 40)
        if speaker:
            draw_text(screen, speaker, self.fonts['speaker'], COLOR_CHAMPAGNE, (speaker_rect[0], speaker_rect[1]))

        if text:
            text_rect = (70, self.dialogue_box_y + 60, SCREEN_WIDTH - 140, self.dialogue_box_height - 80)
            draw_text(screen, text, self.fonts['dialogue'], COLOR_TEXT, (text_rect[0], text_rect[1]), text_rect[2])

    def _draw_control_panel(self, screen):
        """绘制控制面板"""
        if not self.show_controls:
            return

        self._draw_play_button(screen)
        self._draw_progress_bar(screen)
        self._draw_time_display(screen)
        self._draw_hint_text(screen)

    def _draw_play_button(self, screen):
        """绘制播放按钮"""
        button_x = 50
        button_y = SCREEN_HEIGHT - self.control_panel_height + 25
        button_size = self.play_button_size

        button_rect = pygame.Rect(button_x, button_y, button_size, button_size)
        self.player.play_button_rect = button_rect

        color = COLOR_CHAMPAGNE if self.is_hovering_play else COLOR_CHAMPAGNE
        pygame.draw.circle(screen, (*COLOR_PANEL_BORDER, 255), button_rect.center, button_size // 2, 2)

        if self.player.playback_state == PlaybackState.PLAYING:
            bar_width = 8
            bar_height = 20
            pygame.draw.rect(screen, COLOR_CHAMPAGNE, (button_x + 15, button_y + 15, bar_width, bar_height))
            pygame.draw.rect(screen, COLOR_CHAMPAGNE, (button_x + 27, button_y + 15, bar_width, bar_height))
        else:
            points = [
                (button_x + 15, button_y + 12),
                (button_x + 15, button_y + 38),
                (button_x + 38, button_y + 25)
            ]
            pygame.draw.polygon(screen, COLOR_CHAMPAGNE, points)

    def _draw_progress_bar(self, screen):
        """绘制进度条"""
        bar_x = 120
        bar_y = SCREEN_HEIGHT - 55
        bar_width = SCREEN_WIDTH - 280
        bar_height = self.progress_bar_height

        self.player.progress_bar_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)

        progress = self.player.get_progress()
        progress_width = int(bar_width * progress)

        if progress_width > 0:
            progress_rect = pygame.Rect(bar_x, bar_y, progress_width, bar_height)
            pygame.draw.rect(screen, COLOR_CHAMPAGNE, progress_rect, 0, 5)

        knob_x = bar_x + progress_width
        knob_radius = 12
        pygame.draw.circle(screen, COLOR_CHAMPAGNE, (knob_x, bar_y + bar_height // 2), knob_radius)

    def _draw_time_display(self, screen):
        """绘制时间显示"""
        time_text = f"{self.player.get_current_time_text()} / {self.player.get_total_time_text()}"
        time_x = SCREEN_WIDTH - 120
        time_y = SCREEN_HEIGHT - self.control_panel_height + 30

        draw_text(screen, time_text, self.fonts['time'], COLOR_TEXT, (time_x, time_y))

    def _draw_hint_text(self, screen):
        """绘制提示文本"""
        hints = [
            "空格: 播放/暂停",
            "点击: 显示控制条",
            "← →: 快退/快进",
            "ESC: 跳过"
        ]

        hint_y = SCREEN_HEIGHT - self.control_panel_height + 5
        total_width = sum(self.fonts['hint'].size(h)[0] for h in hints) + len(hints) * 40
        start_x = SCREEN_WIDTH - total_width - 20

        for i, hint in enumerate(hints):
            hint_x = start_x + sum(self.fonts['hint'].size(hints[j])[0] + 40 for j in range(i))
            draw_text(screen, hint, self.fonts['hint'], COLOR_PANEL_BORDER, (hint_x, hint_y))

    def _draw_buffering_hint(self, screen):
        """绘制轻量缓冲提示。"""
        if not self.player.is_buffering:
            return

        text = "缓冲中..."
        text_surface = self.fonts['hint'].render(text, True, COLOR_CHAMPAGNE)
        padding_x = 16
        padding_y = 8
        width = text_surface.get_width() + padding_x * 2
        height = text_surface.get_height() + padding_y * 2
        x = SCREEN_WIDTH - width - 30
        y = 100

        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        surface.fill((*COLOR_PANEL, 190))
        pygame.draw.rect(surface, (*COLOR_CHAMPAGNE, 180), (0, 0, width, height), 1, border_radius=8)
        screen.blit(surface, (x, y))
        screen.blit(text_surface, (x + padding_x, y + padding_y))

    def _draw_fade_overlay(self, screen):
        """绘制淡入遮罩"""
        if self.fade_in < 1.0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            alpha = int(255 * (1.0 - self.fade_in))
            overlay.fill(COLOR_BG_DARK)
            overlay.set_alpha(alpha)
            screen.blit(overlay, (0, 0))
