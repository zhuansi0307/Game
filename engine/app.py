"""
应用主类
负责初始化pygame、创建窗口、管理主循环
"""

import sys
import pygame
from pygame.locals import DOUBLEBUF, OPENGL
from .constants import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, COLOR_BG_DARK
from .asset_manager import AssetManager
from .scene_manager import SceneManager
from .config_validator import validate_content_references
from .audio_manager import get_audio_manager
from .gl_renderer import GLRenderer


class App:
    """游戏应用主类"""

    def __init__(self, title="甜妹拯救计划"):
        """
        初始化应用
        :param title: 窗口标题
        """
        # 初始化pygame
        pygame.init()

        # 初始化音频
        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"[警告] 音频初始化失败: {e}")

        # 加载音量设置
        from .config_manager import config_manager
        if pygame.mixer.get_init():
            pygame.mixer.music.set_volume(config_manager.get_music_volume() / 100.0)

        # 禁用系统光标，使用自定义
        pygame.mouse.set_visible(True)

        # 创建窗口（统一使用 OpenGL 模式，避免场景切换时窗口重建闪烁）
        self.screen = self._create_window(DOUBLEBUF | OPENGL)
        pygame.display.set_caption(title)

        # OpenGL 渲染器（用于 pygame 场景）
        self.gl_renderer = GLRenderer()

        # 创建时钟
        self.clock = pygame.time.Clock()

        # 初始化资源管理器
        self.asset_manager = AssetManager()

        # 初始化场景管理器
        self.scene_manager = SceneManager()

        # 注册所有场景
        self._register_scenes()

        # 启动时校验内容引用，缺资源时给出明确日志
        validate_content_references(self.asset_manager, self.scene_manager)

        # 默认进入主菜单
        self.scene_manager.change_scene("main_menu")

        # 运行状态
        self.running = True

        # 上一帧时间
        self.last_time = pygame.time.get_ticks()

        print("[应用] 初始化完成")

    def _register_scenes(self):
        """注册所有游戏场景"""
        # 延迟导入避免循环依赖
        from scenes.main_menu_scene import MainMenuScene
        from scenes.explore_scene import ExploreScene
        from scenes.dialogue_scene import DialogueScene
        from scenes.save_menu_scene import SaveMenuScene
        from scenes.settings_scene import SettingsScene
        from scenes.cutscene_scene import CutsceneScene
        from scenes.chooser_scene import ChooserScene

        # 注册主菜单
        self.scene_manager.register("main_menu", MainMenuScene(self.scene_manager, self.asset_manager))

        # 注册探索场景
        self.scene_manager.register("villa_entrance", ExploreScene(self.scene_manager, self.asset_manager, "villa_entrance"))
        self.scene_manager.register("garage", ExploreScene(self.scene_manager, self.asset_manager, "garage"))
        self.scene_manager.register("restaurant", ExploreScene(self.scene_manager, self.asset_manager, "restaurant"))
        self.scene_manager.register("kitchen", ExploreScene(self.scene_manager, self.asset_manager, "kitchen"))
        self.scene_manager.register("living_right_area", ExploreScene(self.scene_manager, self.asset_manager, "living_right_area"))
        self.scene_manager.register("living_room", ExploreScene(self.scene_manager, self.asset_manager, "living_room"))
        self.scene_manager.register("living_left_area", ExploreScene(self.scene_manager, self.asset_manager, "living_left_area"))
        self.scene_manager.register("second_floor_hallway", ExploreScene(self.scene_manager, self.asset_manager, "second_floor_hallway"))
        self.scene_manager.register("gaoshou_room", ExploreScene(self.scene_manager, self.asset_manager, "gaoshou_room"))
        self.scene_manager.register("liuxin_room", ExploreScene(self.scene_manager, self.asset_manager, "liuxin_room"))
        self.scene_manager.register("study_room", ExploreScene(self.scene_manager, self.asset_manager, "study_room"))
        self.scene_manager.register("master_bedroom", ExploreScene(self.scene_manager, self.asset_manager, "master_bedroom"))
        self.scene_manager.register("master_bedroom_area", ExploreScene(self.scene_manager, self.asset_manager, "master_bedroom_area"))
        self.scene_manager.register("master_bedroom_bathroom", ExploreScene(self.scene_manager, self.asset_manager, "master_bedroom_bathroom"))
        self.scene_manager.register("basement_left", ExploreScene(self.scene_manager, self.asset_manager, "basement_left"))
        self.scene_manager.register("basement_bar", ExploreScene(self.scene_manager, self.asset_manager, "basement_bar"))
        self.scene_manager.register("basement_courtyard", ExploreScene(self.scene_manager, self.asset_manager, "basement_courtyard"))
        self.scene_manager.register("basement_cinema", ExploreScene(self.scene_manager, self.asset_manager, "basement_cinema"))
        self.scene_manager.register("basement_right", ExploreScene(self.scene_manager, self.asset_manager, "basement_right"))
        self.scene_manager.register("gym", ExploreScene(self.scene_manager, self.asset_manager, "gym"))
        self.scene_manager.register("apartment", ExploreScene(self.scene_manager, self.asset_manager, "apartment"))
        self.scene_manager.register("street", ExploreScene(self.scene_manager, self.asset_manager, "street"))

        # 注册对话场景
        self.scene_manager.register("dialogue", DialogueScene(self.scene_manager, self.asset_manager))

        # 注册过场动画场景
        self.scene_manager.register("cutscene", CutsceneScene(self.scene_manager, self.asset_manager))

        # 注册选择场景
        self.scene_manager.register("chooser", ChooserScene(self.scene_manager, self.asset_manager))

        # 注册存档菜单
        self.scene_manager.register("save_menu", SaveMenuScene(self.scene_manager, self.asset_manager))

        # 注册设置菜单
        self.scene_manager.register("settings", SettingsScene(self.scene_manager, self.asset_manager))

    def _create_window(self, flags):
        """创建 OpenGL 窗口；高采样失败时自动降级。"""
        self._set_gl_attributes(samples=8)
        try:
            return pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        except pygame.error as e:
            print(f"[警告] OpenGL 8x MSAA 窗口创建失败，降级为无 MSAA: {e}")
            self._set_gl_attributes(samples=0)
            return pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)

    def _set_gl_attributes(self, samples=8):
        """配置 OpenGL 窗口属性，提升 HUD 和纹理边缘质量。"""
        try:
            pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)
            pygame.display.gl_set_attribute(pygame.GL_DOUBLEBUFFER, 1)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1 if samples else 0)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, samples)
        except pygame.error as e:
            print(f"[警告] OpenGL 抗锯齿属性设置失败: {e}")

    def run(self):
        """运行游戏主循环"""
        print("[应用] 开始游戏主循环")

        while self.running:
            # 计算帧时间
            current_time = pygame.time.get_ticks()
            dt = (current_time - self.last_time) / 1000.0
            self.last_time = current_time

            # 处理事件
            for event in pygame.event.get():
                self._handle_event(event)

            # 更新当前场景
            get_audio_manager().update()
            self.scene_manager.update(dt)

            # 绘制当前场景（传入 gl_renderer 用于 pygame 场景在 OpenGL 窗口中渲染）
            self.scene_manager.draw(self.screen, self.gl_renderer)

            # 更新显示
            pygame.display.flip()

            # 控制帧率
            self.clock.tick(FPS)

        # 游戏退出
        self.quit()

    def _handle_event(self, event):
        """处理事件"""
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # ESC 键由各场景自行处理
                pass
            elif event.key == pygame.K_F11:
                # F11 切换全屏
                self._toggle_fullscreen()

        # 传递给当前场景
        result = self.scene_manager.handle_event(event)
        if result == "quit":
            self.running = False

    def _toggle_fullscreen(self):
        """切换全屏模式"""
        flags = self.screen.get_flags()
        if flags & pygame.FULLSCREEN:
            self.screen = self._create_window(DOUBLEBUF | OPENGL)
        else:
            self.screen = self._create_window(DOUBLEBUF | OPENGL | pygame.FULLSCREEN)

    def quit(self):
        """退出游戏"""
        print("[应用] 退出游戏")
        pygame.quit()
        sys.exit()
