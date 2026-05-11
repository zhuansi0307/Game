"""
探索场景
可复用的探索/互动场景，支持背景图和光点式热区
支持时间系统（不同时段显示不同背景）
"""

import pygame
from engine.constants import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG_DARK
from engine.scene_manager import BaseScene
from engine.hotspot import Hotspot
from engine.game_state import get_game_state
from engine.task_manager import get_task_manager
from engine.audio_manager import get_audio_manager
from ui.chapter_ui import ChapterUI
from ui.task_ui import TaskUI
from ui.map_ui import MapUI
from ui.glass_hud import ExploreGlassHUD


class ExploreScene(BaseScene):
    """探索场景"""

    def __init__(self, scene_manager, asset_manager, scene_id):
        super().__init__(scene_manager)
        self.asset_manager = asset_manager
        self.scene_id = scene_id

        self.scene_data = None
        self.background = None
        self.hotspots = []
        self.title = ""
        self.time_variants = {}  # 时间变体背景 {"morning": path, "noon": path, ...}

        self.fonts = {
            'title': asset_manager.load_font(28),
            'small': asset_manager.load_font(18),
            'desc': asset_manager.load_font(20)
        }

        self.mouse_pos = (0, 0)
        self.fade_in = 0.0
        self.game_time = 0.0
        self.pending_task_step = None

        # 回溯功能
        self.rewind_animating = False
        self.rewind_progress = 0.0
        self.rewind_message = ""

        self.chapter_ui = ChapterUI()
        self.task_ui = TaskUI()
        self.map_ui = MapUI(asset_manager)
        self.glass_hud = ExploreGlassHUD()
        self.task_manager = get_task_manager(asset_manager)
        self.audio_manager = get_audio_manager()
        self.cutscenes_by_id = {
            cutscene.get("id"): cutscene
            for cutscene in asset_manager.load_cutscenes().get("cutscenes", [])
            if cutscene.get("id")
        }

        self._load_scene_data()
        self._load_background_for_time()

        print(f"[探索场景] 初始化场景: {scene_id}")

    def _load_scene_data(self):
        """加载场景配置"""
        scenes_data = self.asset_manager.load_scenes()
        scenes = scenes_data.get("scenes", [])
        
        scene_list = [s for s in scenes if s.get("id") == self.scene_id]

        for scene in scene_list:
            if scene:
                self.scene_data = scene
                self.title = scene.get("title", self.scene_id)
                self.time_variants = scene.get("time_variants", {})

                self.hotspots = []
                for hs_data in scene.get("hotspots", []):
                    hotspot = Hotspot(
                        hotspot_data=hs_data,
                        scene_manager=self.scene_manager,
                        return_scene_id=self.scene_id
                    )
                    self.hotspots.append(hotspot)

                break

        if not self.scene_data:
            print(f"[警告] 未找到场景配置: {self.scene_id}")

    def _load_background_for_time(self):
        """根据当前时间加载背景"""
        if self.time_variants:
            gs = get_game_state()
            current_period = gs.game_time.get_period_name()
            
            bg_path = self.time_variants.get(current_period)
            if bg_path:
                self.background = self.asset_manager.load_image(
                    bg_path,
                    fallback_size=(SCREEN_WIDTH, SCREEN_HEIGHT)
                )
            elif self.time_variants:
                first_path = list(self.time_variants.values())[0]
                self.background = self.asset_manager.load_image(
                    first_path,
                    fallback_size=(SCREEN_WIDTH, SCREEN_HEIGHT)
                )
        else:
            bg_path = self.scene_data.get("background", "") if self.scene_data else ""
            if bg_path:
                self.background = self.asset_manager.load_image(
                    bg_path,
                    fallback_size=(SCREEN_WIDTH, SCREEN_HEIGHT)
                )

    def _switch_time_period(self):
        """切换时间段（循环）"""
        if not self.time_variants:
            return
        
        gs = get_game_state()
        gs.next_time_period()
        self._load_background_for_time()
        print(f"[探索场景] 时间切换到: {gs.game_time.get_display_text()}")

    def on_enter(self, **kwargs):
        """进入场景时调用"""
        self.fade_in = 0.0
        self._load_background_for_time()

        gs = get_game_state()
        gs.current_scene = self.scene_id

        self.task_manager.bind_ui(self.task_ui)
        self.task_manager.update_task_availability(gs)

        self._update_hotspot_visibility(gs)

        self.pending_task_step = None
        if kwargs.get("task_callback") == "advance_task":
            previous_time_key = gs.game_time.get_full_time_key()
            self.pending_task_step = self.task_manager.advance_current_task(gs)
            self._refresh_after_time_change(previous_time_key)
            print(f"[探索场景] 任务推进回到场景: {self.scene_id}")
            return

        triggered_task = self.task_manager.check_and_trigger_task(
            self.scene_id,
            gs,
            event_type="scene_enter"
        )

        if triggered_task:
            current_step = triggered_task.get_current_step()
            if current_step:
                self.pending_task_step = current_step

        print(f"[探索场景] 进入场景: {self.scene_id}")
        self._debug_hotspots()

    def _process_task_step(self, step):
        """处理任务步骤"""
        step_type = step.type

        if step_type == "dialogue" and step.dialogue_id:
            self.scene_manager.change_scene("dialogue",
                dialogue_id=step.dialogue_id,
                return_scene=self.scene_id,
                task_callback="advance_task")

        elif step_type == "cutscene" and step.cutscene_id:
            if self._play_audio_cutscene_in_background(step):
                return
            self.scene_manager.change_scene("cutscene",
                cutscene_id=step.cutscene_id,
                return_scene=self.scene_id,
                callback="advance_task")

        elif step_type == "cutscene_arrive" and step.cutscene_id:
            if self._play_audio_cutscene_in_background(step):
                return
            if not step.target_scene:
                return
            self.scene_manager.change_scene("cutscene",
                cutscene_id=step.cutscene_id,
                arrive_scene=step.target_scene,
                callback="advance_task")

        elif step_type in ("choice", "chooser"):
            self.scene_manager.change_scene("chooser",
                background=step.raw.get("background"),
                choices=step.choices,
                return_scene=self.scene_id,
                task_callback="advance_task")

        elif step_type == "scene_transition" and step.target_scene:
            if step.target_scene == "chooser":
                self.scene_manager.change_scene("chooser",
                    background=step.raw.get("background"),
                    choices=step.choices,
                    return_scene=self.scene_id,
                    task_callback="advance_task")
            else:
                self.scene_manager.change_scene(step.target_scene, task_callback="advance_task")

        elif step_type == "complete":
            gs = get_game_state()
            previous_time_key = gs.game_time.get_full_time_key()
            self.task_manager.advance_current_task(gs)
            self._refresh_after_time_change(previous_time_key)
            self.scene_manager.change_scene(step.target_scene or self.scene_id)

    def _play_audio_cutscene_in_background(self, step):
        cutscene = self.cutscenes_by_id.get(step.cutscene_id)
        if not cutscene:
            return False

        audio_path = cutscene.get("audio")
        if not audio_path or cutscene.get("video"):
            return False

        self.audio_manager.play_asset(self.asset_manager, audio_path)
        gs = get_game_state()
        previous_time_key = gs.game_time.get_full_time_key()
        self.pending_task_step = self.task_manager.advance_current_task(gs)
        self._refresh_after_time_change(previous_time_key)
        return True

    def _refresh_after_time_change(self, previous_time_key):
        gs = get_game_state()
        current_time_key = gs.game_time.get_full_time_key()
        if current_time_key == previous_time_key:
            return

        self._load_background_for_time()
        self.task_manager.update_task_availability(gs)
        self._update_hotspot_visibility(gs)
        print(f"[explore] time changed, refreshed scene background: {current_time_key}")

    def handle_event(self, event):
        """处理事件"""
        if event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos

        # 先让地图UI处理事件
        if self.map_ui.handle_event(event):
            return True

        # 地图打开时阻止鼠标点击穿透到底层热区。
        if self.map_ui.visible and event.type == pygame.MOUSEBUTTONDOWN:
            return True

        if not self.map_ui.visible and self.glass_hud.handle_event(event, self):
            return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                click_pos = event.pos

                clicked_hotspot = None
                for hotspot in self._iter_visible_hotspots():
                    if hotspot.is_hovered_check(click_pos):
                        clicked_hotspot = hotspot
                        break

                if clicked_hotspot:
                    self._handle_hotspot_click(clicked_hotspot)
                    return True

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.scene_manager.change_scene("main_menu")
            elif event.key == pygame.K_t and self.time_variants:
                self._switch_time_period()
            elif event.key == pygame.K_r:
                self._trigger_rewind()
            elif event.key == pygame.K_m:
                self.map_ui.toggle()
                return True

        return False

    def _trigger_rewind(self):
        """触发时间回溯"""
        gs = get_game_state()
        if gs.game_time.can_rewind():
            gs.rewind_time()
            self._load_background_for_time()
            self.rewind_animating = True
            self.rewind_progress = 0.0
            self.rewind_message = "⏪ 时间回溯"
            print(f"[探索场景] 时间回溯到: {gs.game_time.get_display_text()}")
        else:
            self.rewind_message = "已到达第一天"
            self.rewind_animating = True
            self.rewind_progress = 0.0

    def _handle_hotspot_click(self, hotspot):
        """处理热区点击"""
        gs = get_game_state()
        gs.add_click()

        triggered_task = self.task_manager.check_and_trigger_task(
            self.scene_id,
            gs,
            hotspot_id=hotspot.id,
            event_type="hotspot_click"
        )
        
        if triggered_task:
            current_step = triggered_task.get_current_step()
            if current_step:
                self.pending_task_step = current_step
            hotspot.activate(navigate=False)
            return

        if self._is_hotspot_blocked(hotspot, gs):
            self.task_ui.show_notification(getattr(hotspot, "blocked_message", "禁止进入"), 2.5)
            return

        hotspot.activate(navigate=True)

    def _is_hotspot_blocked(self, hotspot, gs):
        """根据热区配置判断当前是否禁止默认进入。"""
        conditions = getattr(hotspot, "blocked_when", [])
        if isinstance(conditions, dict):
            conditions = [conditions]
        return bool(conditions) and all(gs.check_condition(condition) for condition in conditions)

    def update(self, dt):
        """每帧更新"""
        if self.fade_in < 1.0:
            self.fade_in += dt * 10
            if self.fade_in > 1.0:
                self.fade_in = 1.0

        self.game_time += dt

        self.chapter_ui.update(dt)
        self.task_ui.update(dt)
        self.task_manager.update_notifications(dt)
        self.task_ui.set_guidance(self.task_manager.get_guidance(self.scene_id, get_game_state()))
        self.mouse_pos = pygame.mouse.get_pos()
        self.glass_hud.update(dt, self.mouse_pos, pygame.mouse.get_pressed()[0], self)

        world_mouse = (-9999, -9999) if self.map_ui.visible or self.glass_hud.is_hovering() else self.mouse_pos
        for hotspot in self._iter_visible_hotspots():
            hotspot.update(dt, world_mouse)

        if self.pending_task_step and self.fade_in >= 1.0:
            step = self.pending_task_step
            self.pending_task_step = None
            self._process_task_step(step)

        # 回溯动画更新
        if self.rewind_animating:
            self.rewind_progress += dt * 2
            if self.rewind_progress >= 1.0:
                self.rewind_animating = False
                self.rewind_progress = 0.0
                self.rewind_message = ""

    def draw(self, screen):
        """绘制场景"""
        self._draw_background(screen)
        self.chapter_ui.draw(screen)
        self.map_ui.draw(screen)

        if self.fade_in < 1.0:
            fade_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            fade_surface.fill(COLOR_BG_DARK)
            fade_surface.set_alpha(int(255 * (1 - self.fade_in)))
            screen.blit(fade_surface, (0, 0))

        # 绘制回溯效果
        if self.rewind_animating:
            self._draw_rewind_effect(screen)

    def draw_gl_overlay(self):
        """绘制探索场景的原生 OpenGL HUD 叠层。"""
        self.glass_hud.draw_gl(self, alpha=self.fade_in)

    def _draw_background(self, screen):
        """绘制背景"""
        if self.background:
            bg_rect = self.background.get_rect()
            if bg_rect.width != SCREEN_WIDTH or bg_rect.height != SCREEN_HEIGHT:
                scaled_bg = pygame.transform.smoothscale(
                    self.background, (SCREEN_WIDTH, SCREEN_HEIGHT)
                )
                screen.blit(scaled_bg, (0, 0))
            else:
                screen.blit(self.background, (0, 0))
        else:
            screen.fill((50, 55, 65))

    def _update_hotspot_visibility(self, gs):
        """更新热区可见性，根据unlock_tasks和前置任务完成状态"""
        for hotspot in self.hotspots:
            if hasattr(hotspot, 'unlock_tasks') and hotspot.unlock_tasks:
                all_completed = all(
                    self.task_manager.is_task_completed(task_id, gs)
                    for task_id in hotspot.unlock_tasks
                )
                if all_completed:
                    hotspot.hidden = False
                    print(f"[探索场景] 热区 {hotspot.id} 解锁显示（前置任务全部完成）")
                else:
                    hotspot.hidden = True

    def _iter_visible_hotspots(self):
        """只返回当前任务链允许渲染的热区。"""
        gs = get_game_state()
        for hotspot in self.hotspots:
            if getattr(hotspot, 'destroyed', False):
                continue
            has_default_navigation = bool(hotspot.target_scene or hotspot.target_dialogue)
            if self.task_manager.should_render_hotspot_ui(
                self.scene_id,
                hotspot.id,
                gs,
                has_default_navigation=has_default_navigation,
            ):
                yield hotspot

    def _debug_hotspots(self):
        """调试：打印当前场景热区信息"""
        for hs in self.hotspots:
            print(f"  热区: {hs.id}, render_type={getattr(hs, 'render_type', 'dot')}, "
                  f"one_time={getattr(hs, 'one_time', False)}, destroyed={getattr(hs, 'destroyed', False)}, "
                  f"hidden={hs.hidden}, rect={hs.rect}, dot={hs.dot_pos}")

    def show_chapter_start(self, chapter_num, title, subtitle="", description=""):
        """显示章节开始标题"""
        self.chapter_ui.show_chapter_start(chapter_num, title, subtitle, description)

    def show_chapter_complete(self, chapter_num, title):
        """显示章节完成"""
        self.chapter_ui.show_chapter_complete(chapter_num, title)

    def show_task_notification(self, message, duration=3.0):
        """显示任务通知"""
        self.task_ui.show_notification(message, duration)

    def _draw_rewind_effect(self, screen):
        """绘制回溯特效"""
        # 淡蓝色闪烁效果
        alpha = int(100 * (1 - self.rewind_progress))
        flash_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        flash_surface.fill((180, 200, 255))
        flash_surface.set_alpha(alpha)
        screen.blit(flash_surface, (0, 0))

        # 显示回溯消息
        if self.rewind_message and self.rewind_progress < 0.7:
            font = self.fonts['title']
            text_surface = font.render(self.rewind_message, True, (255, 255, 255))
            text_rect = text_surface.get_rect(center=(SCREEN_WIDTH // 2, 100))
            screen.blit(text_surface, text_rect)
