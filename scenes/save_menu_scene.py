"""
存档菜单场景
存档界面，支持保存和加载游戏
"""

import pygame
from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG_DARK, COLOR_TEXT, COLOR_CHAMPAGNE
from engine.scene_manager import BaseScene
from engine.save_manager import get_save_manager
from engine.game_state import get_game_state


class SaveMenuScene(BaseScene):

    def __init__(self, scene_manager, asset_manager):
        super().__init__(scene_manager)
        self.asset_manager = asset_manager
        self.save_manager = get_save_manager()

        self.font_title = asset_manager.load_font(48)
        self.font_text = asset_manager.load_font(28)
        self.font_meta = asset_manager.load_font(22)
        self.font_button = asset_manager.load_font(32)

        self.mouse_pos = (0, 0)
        self.fade_in = 0.0

        self.max_slots = 5
        self.slot_height = 96
        self.slot_start_y = 128

        self.slot_rects = []
        self._create_buttons()

        self.mode = "menu"
        self.selected_slot = None

        print("[存档菜单] 初始化完成")

    def _create_buttons(self):
        self.slot_rects = []

        slot_width = 720
        slot_height = self.slot_height
        slot_x = SCREEN_WIDTH // 2 - slot_width // 2

        for i in range(1, self.max_slots + 1):
            y = self.slot_start_y + (i - 1) * (slot_height + 10)
            self.slot_rects.append({
                "rect": pygame.Rect(slot_x, y, slot_width, slot_height),
                "slot": i
            })

        back_y = self.slot_start_y + self.max_slots * (slot_height + 12) + 28
        self.back_button = pygame.Rect(SCREEN_WIDTH // 2 - 100, back_y, 200, 50)

    def on_enter(self, **kwargs):
        self.fade_in = 0.0
        self.mode = "menu"
        self.selected_slot = None
        print("[存档菜单] 进入存档菜单")

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self._handle_click(event.pos)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.scene_manager.change_scene("main_menu")
        return False

    def _handle_click(self, pos):
        if self.mode == "menu":
            for slot_data in self.slot_rects:
                if slot_data["rect"].collidepoint(pos):
                    self.selected_slot = slot_data["slot"]
                    self.mode = "confirm"
                    return

            if self.back_button.collidepoint(pos):
                self.scene_manager.change_scene("main_menu")

        elif self.mode == "confirm":
            save_rect = pygame.Rect(SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 + 40, 180, 50)
            load_rect = pygame.Rect(SCREEN_WIDTH // 2 + 20, SCREEN_HEIGHT // 2 + 40, 180, 50)
            back_rect = pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 100, 200, 50)

            if save_rect.collidepoint(pos):
                self._do_save(self.selected_slot)
                self.mode = "menu"
            elif load_rect.collidepoint(pos):
                self._do_load(self.selected_slot)
            elif back_rect.collidepoint(pos):
                self.mode = "menu"
                self.selected_slot = None

    def _do_save(self, slot):
        try:
            gs = get_game_state()
            gs.current_scene = gs.current_scene if gs.current_scene else "second_floor_hallway"
            result = self.save_manager.save_game(slot)
            print(f"[存档菜单] 保存{'成功' if result else '失败'}，槽位 {slot}")
        except Exception as e:
            print(f"[存档菜单] 保存异常: {e}")

    def _do_load(self, slot):
        try:
            result = self.save_manager.load_game(slot)
            if result:
                gs = get_game_state()
                scene = gs.current_scene if gs.current_scene else "second_floor_hallway"
                if scene == "main_menu":
                    scene = "second_floor_hallway"
                if not self.scene_manager.change_scene(scene):
                    scene = "second_floor_hallway"
                    self.scene_manager.change_scene(scene)
                print(f"[存档菜单] 加载成功，场景: {scene}")
            else:
                print(f"[存档菜单] 加载失败")
        except Exception as e:
            print(f"[存档菜单] 加载异常: {e}")

    def update(self, dt):
        if self.fade_in < 1.0:
            self.fade_in = min(1.0, self.fade_in + dt * 2)

    def draw(self, screen):
        screen.fill(COLOR_BG_DARK)

        if self.mode == "menu":
            self._draw_menu(screen)
        elif self.mode == "confirm":
            self._draw_confirm(screen)

        if self.fade_in < 1.0:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(int(255 * (1 - self.fade_in)))
            screen.blit(overlay, (0, 0))

    def _draw_menu(self, screen):
        title = "存档 / 读档"
        title_surf = self.font_title.render(title, True, COLOR_CHAMPAGNE)
        title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, 60))
        screen.blit(title_surf, title_rect)

        for slot_data in self.slot_rects:
            info = self.save_manager.get_save_info(slot_data["slot"])
            self._draw_slot(screen, slot_data["rect"], slot_data["slot"], info, slot_data["rect"].collidepoint(self.mouse_pos))

        self._draw_back_button(screen, self.back_button.collidepoint(self.mouse_pos))

    def _draw_slot(self, screen, rect, slot_num, info, hovered):
        border_color = (200, 160, 80) if hovered else (80, 70, 60)
        bg_color = (35, 35, 40) if hovered else (25, 25, 30)

        pygame.draw.rect(screen, bg_color, rect, border_radius=8)
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=8)

        text_color = COLOR_CHAMPAGNE if hovered else COLOR_TEXT

        if info.get("exists"):
            scene = info.get("current_scene", "unknown")
            text1 = f"存档 #{slot_num}"
            text2 = f"场景: {scene}"
            text3 = info.get("timestamp", "")[:19].replace("T", " ")
        else:
            text1 = f"存档 #{slot_num}"
            text2 = "空"
            text3 = ""

        surf1 = self.font_button.render(text1, True, text_color)
        screen.blit(surf1, (rect.x + 22, rect.y + 12))

        surf2 = self.font_meta.render(text2, True, (150, 154, 164))
        screen.blit(surf2, (rect.x + 24, rect.y + 48))

        if text3:
            surf3 = self.font_meta.render(text3, True, (108, 113, 123))
            screen.blit(surf3, (rect.x + 24, rect.y + 70))

    def _draw_back_button(self, screen, hovered):
        bg_alpha = 220 if hovered else 180
        border_color = (200, 160, 80) if hovered else (80, 70, 60)

        btn_surface = pygame.Surface((200, 50), pygame.SRCALPHA)
        btn_surface.fill((50, 45, 40, bg_alpha))
        pygame.draw.rect(btn_surface, border_color, btn_surface.get_rect(), 2, border_radius=8)

        x, y = self.back_button.x, self.back_button.y
        screen.blit(btn_surface, (x, y))

        text_surf = self.font_text.render("返回主菜单", True, COLOR_CHAMPAGNE if hovered else (180, 175, 165))
        text_rect = text_surf.get_rect(center=self.back_button.center)
        screen.blit(text_surf, text_rect)

    def _draw_confirm(self, screen):
        info = self.save_manager.get_save_info(self.selected_slot)

        panel_w, panel_h = 480, 260
        panel_x = SCREEN_WIDTH // 2 - panel_w // 2
        panel_y = SCREEN_HEIGHT // 2 - panel_h // 2

        pygame.draw.rect(screen, (25, 25, 30), (panel_x, panel_y, panel_w, panel_h), border_radius=12)
        pygame.draw.rect(screen, (60, 55, 50), (panel_x, panel_y, panel_w, panel_h), 2, border_radius=12)

        title = f"槽位 #{self.selected_slot}"
        subtitle = f"已有存档" if info.get("exists") else "空存档"
        if info.get("exists"):
            subtitle += f" | 场景: {info.get('current_scene', 'unknown')}"

        t1 = self.font_title.render(title, True, COLOR_CHAMPAGNE)
        t2 = self.font_text.render(subtitle, True, (150, 155, 165))
        t3 = self.font_text.render("点击下方按钮保存或加载", True, (100, 105, 115))

        screen.blit(t1, t1.get_rect(center=(SCREEN_WIDTH // 2, panel_y + 50)))
        screen.blit(t2, t2.get_rect(center=(SCREEN_WIDTH // 2, panel_y + 90)))
        screen.blit(t3, t3.get_rect(center=(SCREEN_WIDTH // 2, panel_y + 120)))

        btn_y = panel_y + 160
        self._draw_action_button(screen, SCREEN_WIDTH // 2 - 190, btn_y, 180, 50, "保存游戏", info.get("exists"))
        self._draw_action_button(screen, SCREEN_WIDTH // 2 + 10, btn_y, 180, 50, "加载游戏", True)
        self._draw_action_button(screen, SCREEN_WIDTH // 2 - 100, btn_y + 60, 200, 50, "取消", False)

    def _draw_action_button(self, screen, x, y, w, h, text, enabled):
        hovered = pygame.Rect(x, y, w, h).collidepoint(self.mouse_pos) if enabled else False
        bg_alpha = 220 if hovered else 180
        border_color = (200, 160, 80) if hovered else (80, 70, 60)
        text_color = COLOR_CHAMPAGNE if enabled else (80, 80, 85)

        btn_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        btn_surface.fill((50, 45, 40, bg_alpha))
        pygame.draw.rect(btn_surface, border_color, btn_surface.get_rect(), 2, border_radius=8)

        screen.blit(btn_surface, (x, y))

        text_surf = self.font_button.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=(x + w // 2, y + h // 2))
        screen.blit(text_surf, text_rect)
