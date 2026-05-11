"""
场景管理器模块
负责管理游戏中的所有场景，包括场景注册、切换等
"""

from abc import ABC, abstractmethod


class BaseScene(ABC):
    """场景基类，所有场景都需要继承此类"""

    def __init__(self, scene_manager):
        """
        初始化场景
        :param scene_manager: 场景管理器引用
        """
        self.scene_manager = scene_manager

    @abstractmethod
    def on_enter(self, **kwargs):
        """
        进入场景时调用
        :param kwargs: 传入的参数（如对话ID、返回场景等）
        """
        pass

    @abstractmethod
    def handle_event(self, event):
        """
        处理事件
        :param event: pygame事件对象
        :return: True表示事件已处理，False表示需要继续传递
        """
        pass

    @abstractmethod
    def update(self, dt):
        """
        每帧更新
        :param dt: 距离上一帧的时间（秒）
        """
        pass

    @abstractmethod
    def draw(self, screen):
        """
        绘制场景
        :param screen: pygame屏幕surface
        """
        pass


class SceneManager:
    """场景管理器"""

    def __init__(self):
        self.scenes = {}  # 已注册的场景字典
        self.current_scene = None  # 当前场景
        self.current_scene_name = None  # 当前场景名称
        self.prev_scene_name = None  # 上一个场景名称（用于返回）
        self.scene_kwargs = {}  # 传递给场景的参数

    def register(self, name, scene):
        """
        注册场景
        :param name: 场景名称（唯一标识）
        :param scene: BaseScene实例
        """
        if not isinstance(scene, BaseScene):
            raise TypeError(f"场景 {name} 必须继承 BaseScene")
        self.scenes[name] = scene
        print(f"[场景管理器] 已注册场景: {name}")

    def change_scene(self, name, **kwargs):
        """
        切换场景
        :param name: 目标场景名称
        :param kwargs: 传递给目标场景的参数
        """
        if name not in self.scenes:
            print(f"[错误] 场景 {name} 未注册!")
            return False

        # 保存当前场景名称
        if self.current_scene_name:
            self.prev_scene_name = self.current_scene_name

        self.current_scene_name = name
        self.scene_kwargs = kwargs

        # 获取新场景并调用 on_enter
        self.current_scene = self.scenes[name]

        # 如果上一个场景声明了 on_leave，调用它
        if self.prev_scene_name and hasattr(self.scenes.get(self.prev_scene_name), "on_leave"):
            self.scenes[self.prev_scene_name].on_leave()

        self.current_scene.on_enter(**kwargs)

        print(f"[场景管理器] 切换到场景: {name}")
        return True

    def get_current_scene(self):
        """获取当前场景"""
        return self.current_scene

    def get_current_scene_name(self):
        """获取当前场景名称"""
        return self.current_scene_name

    def get_prev_scene_name(self):
        """获取上一个场景名称"""
        return self.prev_scene_name

    def return_to_prev_scene(self, **kwargs):
        """返回上一个场景"""
        if self.prev_scene_name:
            self.change_scene(self.prev_scene_name, **kwargs)

    def handle_event(self, event):
        """将事件传递给当前场景处理"""
        if self.current_scene:
            return self.current_scene.handle_event(event)
        return False

    def update(self, dt):
        """更新当前场景"""
        if self.current_scene:
            self.current_scene.update(dt)

    def draw(self, screen, gl_renderer=None):
        """绘制当前场景
        :param screen: pygame 屏幕 surface
        :param gl_renderer: OpenGL 渲染器（用于 pygame 场景在 OpenGL 窗口中渲染）
        """
        if not self.current_scene:
            return

        # 检查场景是否使用原生 OpenGL 渲染
        if getattr(self.current_scene, 'use_native_gl', False):
            # 场景自己处理 OpenGL 渲染
            self.current_scene.draw(screen)
        elif gl_renderer is not None:
            # pygame 场景：绘制到 surface，然后通过 OpenGL 纹理渲染
            screen.fill((0, 0, 0))
            self.current_scene.draw(screen)
            gl_renderer.render_pygame_surface(screen)
            draw_gl_overlay = getattr(self.current_scene, "draw_gl_overlay", None)
            if draw_gl_overlay:
                draw_gl_overlay()
        else:
            # 标准 pygame 渲染（兼容模式）
            self.current_scene.draw(screen)
