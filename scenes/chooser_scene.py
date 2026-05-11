"""
选择场景
显示选择背景图片和两个选项按钮
"""

import pygame
from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_TEXT, COLOR_CHAMPAGNE, COLOR_PANEL_BORDER
from engine.scene_manager import BaseScene


class ChooserScene(BaseScene):
    """选择场景"""

    def __init__(self, scene_manager, asset_manager):
        super().__init__(scene_manager)
        self.asset_manager = asset_manager

        self.fonts = {
            "title": asset_manager.load_font(48),
            "button": asset_manager.load_font(36),
            "desc": asset_manager.load_font(28),
        }

        self.background_image = None
        self.background_surface = None
        self.background_path = "第一天所有素材/是否帮王琳刷碗？.png"
        self.choices = self._default_choices()
        self.buttons = []
        self.panel_rect = pygame.Rect(72, SCREEN_HEIGHT - 306, 408, 224)
        self._load_background(self.background_path)
        self._layout_buttons()

        self.mouse_pos = (0, 0)
        self.hovered_button = -1
        self.fade_in = 0.0

        self.return_scene = "living_right_area"
        self.task_callback = None

        print("[选择场景] 初始化完成")

    def _default_choices(self):
        return [
            {"text": "帮忙刷碗", "action": "wash"},
            {"text": "不帮忙", "action": "not_wash"},
        ]

    def _load_background(self, bg_path):
        try:
            self.background_image = self.asset_manager.load_image(bg_path)
            self.background_surface = self._fit_background(self.background_image)
            print(f"[选择场景] 加载背景: {bg_path}")
        except Exception as e:
            print(f"[选择场景] 加载背景失败: {e}")
            self.background_image = None
            self.background_surface = None

    def _fit_background(self, image):
        """把选择背景等比居中适配到游戏窗口。"""
        if not image:
            return None

        source_width, source_height = image.get_size()
        if source_width == SCREEN_WIDTH and source_height == SCREEN_HEIGHT:
            return image

        scale = max(SCREEN_WIDTH / source_width, SCREEN_HEIGHT / source_height)
        target_size = (
            int(source_width * scale),
            int(source_height * scale),
        )
        scaled = pygame.transform.smoothscale(image, target_size)

        if target_size == (SCREEN_WIDTH, SCREEN_HEIGHT):
            return scaled

        surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        x = (SCREEN_WIDTH - target_size[0]) // 2
        y = (SCREEN_HEIGHT - target_size[1]) // 2
        surface.blit(scaled, (x, y))
        return surface

    def _layout_buttons(self):
        button_width = 360
        button_height = 60
        button_gap = 18
        panel_width = 408
        panel_height = len(self.choices) * button_height + max(0, len(self.choices) - 1) * button_gap + 56
        panel_height = max(160, panel_height)
        panel_x = 72
        panel_y = SCREEN_HEIGHT - panel_height - 82
        self.panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        button_x = panel_x + (panel_width - button_width) // 2
        button_y = panel_y + 28
        self.buttons = []
        for index, choice in enumerate(self.choices):
            rect = pygame.Rect(button_x, button_y + index * (button_height + button_gap), button_width, button_height)
            self.buttons.append({
                "rect": rect,
                "text": choice.get("text", choice.get("label", f"选择 {index + 1}")),
                "action": choice.get("action", choice.get("id", str(index))),
                "choice": choice,
            })

    def on_enter(self, **kwargs):
        self.fade_in = 0.0
        self.task_callback = kwargs.get("task_callback")
        if kwargs.get("return_scene"):
            self.return_scene = kwargs["return_scene"]
        self.background_path = kwargs.get("background", self.background_path)
        self.choices = kwargs.get("choices") or self._default_choices()
        self._load_background(self.background_path)
        self._layout_buttons()
        print(f"[选择场景] 进入选择场景，return_scene={self.return_scene}")

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            self._update_hover()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._handle_click(event.pos)
                return True
        return True

    def _update_hover(self):
        self.hovered_button = -1
        for i, btn in enumerate(self.buttons):
            if btn["rect"].collidepoint(self.mouse_pos):
                self.hovered_button = i
                break

    def _handle_click(self, pos):
        clicked_index = -1
        for index, button in enumerate(self.buttons):
            if button["rect"].collidepoint(pos):
                clicked_index = index
                break

        if clicked_index >= 0:
            self.hovered_button = clicked_index
            button = self.buttons[clicked_index]
            action = button["action"]
            choice = button["choice"]
            print(f"[选择场景] 点击选项: {action}")
            from engine.game_state import get_game_state
            from engine.task_manager import get_task_manager

            game_state = get_game_state()
            game_state.set_variable("last_choice_result", action)
            if choice.get("variable"):
                game_state.set_variable(choice["variable"], action)

            task_manager = get_task_manager(self.asset_manager)
            task_manager.reward_system.apply(choice.get("reward") or choice, game_state, task_manager.tasks)

            cutscene_id = choice.get("cutscene_id")
            if cutscene_id:
                self.scene_manager.change_scene(
                    "cutscene",
                    cutscene_id=cutscene_id,
                    return_scene=self.return_scene,
                    callback="advance_task" if self.task_callback == "advance_task" else None,
                )
                return

            if self.task_callback == "advance_task":
                self.scene_manager.change_scene(
                    self.return_scene,
                    task_callback="advance_task",
                    choice_result=action,
                )
            else:
                self.scene_manager.change_scene(self.return_scene, choice_result=action)

    def update(self, dt):
        if self.fade_in < 1.0:
            self.fade_in = min(1.0, self.fade_in + dt * 2)

    def render(self, screen):
        if self.background_surface:
            screen.blit(self.background_surface, (0, 0))
        else:
            screen.fill((40, 40, 40))

        panel = pygame.Surface(self.panel_rect.size, pygame.SRCALPHA)
        panel.fill((18, 18, 20, 112))
        pygame.draw.rect(panel, (207, 183, 152, 128), panel.get_rect(), 1, border_radius=10)
        screen.blit(panel, self.panel_rect)

        for i, btn in enumerate(self.buttons):
            is_hover = i == self.hovered_button
            color = (220, 198, 170) if is_hover else COLOR_CHAMPAGNE
            pygame.draw.rect(screen, color, btn["rect"], border_radius=8)
            pygame.draw.rect(screen, (80, 60, 40), btn["rect"], 2, border_radius=8)
            
            text_surf = self.fonts["button"].render(btn["text"], True, (20, 15, 10))
            text_rect = text_surf.get_rect(center=btn["rect"].center)
            screen.blit(text_surf, text_rect)

        if self.fade_in < 1.0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(int(255 * (1 - self.fade_in)))
            screen.blit(overlay, (0, 0))

    def draw(self, screen):
        self.render(screen)
