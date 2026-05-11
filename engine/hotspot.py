"""
热区逻辑模块
只负责热区的交互逻辑（碰撞检测、状态管理、事件处理）
不包含任何渲染代码
"""

import pygame
import math


class Hotspot:
    """
    热区交互逻辑类
    负责：
    - 碰撞检测
    - 状态管理（悬停、发现等）
    - 事件分发
    """

    def __init__(self, hotspot_data, scene_manager, return_scene_id):
        """
        初始化热区
        :param hotspot_data: 热区配置字典
        :param scene_manager: 场景管理器
        :param return_scene_id: 返回场景ID
        """
        self.id = hotspot_data.get("id", "")
        self.scene_manager = scene_manager
        self.return_scene_id = return_scene_id

        rect = hotspot_data.get("rect", [0, 0, 100, 100])
        self.rect = pygame.Rect(rect[0], rect[1], rect[2], rect[3])

        dot = hotspot_data.get("dot")
        if dot:
            self.dot_pos = tuple(dot)
        else:
            self.dot_pos = (self.rect.centerx, self.rect.centery)

        self.title = hotspot_data.get("title", "")
        self.desc = hotspot_data.get("desc", "")
        self.target_scene = hotspot_data.get("target_scene")
        self.target_dialogue = hotspot_data.get("target_dialogue")
        self.discovered = hotspot_data.get("discovered", False)
        self.hidden = hotspot_data.get("hidden", False)
        self.render_type = hotspot_data.get("render_type", "dot")
        self.one_time = hotspot_data.get("one_time", False)
        self.blocked_when = hotspot_data.get("blocked_when", [])
        self.blocked_message = hotspot_data.get("blocked_message", "禁止进入")
        self.unlock_tasks = hotspot_data.get("unlock_tasks", [])
        self.destroyed = False

        self.is_hovered = False
        self.hover_progress = 0.0

        self.callbacks = {
            "on_click": [],
            "on_hover_start": [],
            "on_hover_end": []
        }

    def handle_event(self, event, mouse_pos):
        """
        处理热区事件
        :param event: pygame事件
        :param mouse_pos: 鼠标位置
        :return: True 表示事件已处理
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and self.is_hovered_check(mouse_pos):
                self._on_click()
                return True

        return False

    def is_hovered_check(self, mouse_pos):
        """检查鼠标是否在真实点击区域内"""
        return self.rect.collidepoint(mouse_pos)

    def update(self, dt, mouse_pos):
        """更新热区状态"""
        was_hovered = self.is_hovered
        self.is_hovered = self.is_hovered_check(mouse_pos)

        target = 1.0 if self.is_hovered else 0.0
        if abs(self.hover_progress - target) < 0.01:
            self.hover_progress = target
            if was_hovered == self.is_hovered:
                return

        speed = 1 - math.pow(0.001, min(dt, 0.1) / 0.18)
        self.hover_progress += (target - self.hover_progress) * speed

        if not was_hovered and self.is_hovered:
            self._on_hover_start()
        elif was_hovered and not self.is_hovered:
            self._on_hover_end()

    def _on_click(self):
        """处理点击"""
        self.activate()

    def activate(self, navigate=True):
        """激活热区，可由外层决定是否立即执行默认跳转。"""
        if self.one_time and self.destroyed:
            return

        if navigate:
            if self.target_dialogue:
                self.scene_manager.change_scene(
                    "dialogue",
                    dialogue_id=self.target_dialogue,
                    return_scene=self.return_scene_id
                )
            elif self.target_scene:
                self.scene_manager.change_scene(self.target_scene)

        if not self.discovered:
            self.discovered = True

        if self.one_time:
            self.destroyed = True
            self.hidden = True

        self._trigger_callbacks("on_click")

    def _on_hover_start(self):
        """悬停开始"""
        self._trigger_callbacks("on_hover_start")

    def _on_hover_end(self):
        """悬停结束"""
        self._trigger_callbacks("on_hover_end")

    def add_callback(self, event_type, callback):
        """
        添加事件回调
        :param event_type: 事件类型（on_click, on_hover_start, on_hover_end）
        :param callback: 回调函数
        """
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)

    def remove_callback(self, event_type, callback):
        """移除事件回调"""
        if event_type in self.callbacks and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)

    def _trigger_callbacks(self, event_type):
        """触发指定类型的回调"""
        for callback in self.callbacks.get(event_type, []):
            try:
                callback(self)
            except Exception as e:
                print(f"[错误] 回调执行失败: {e}")

    def is_active(self):
        """检查热区是否激活（可见且可交互）"""
        return not self.hidden

    def can_click(self):
        """检查热区是否可以点击"""
        return self.is_hovered_check(self.dot_pos)

    def get_interaction_hint(self):
        """获取交互提示"""
        if self.target_dialogue:
            return f"与 {self.title} 对话"
        elif self.target_scene:
            return f"前往 {self.title}"
        return self.title

    def reset(self):
        """重置热区状态"""
        self.discovered = False
        self.hover_progress = 0.0
        self.is_hovered = False

    def set_discovered(self, discovered):
        """设置发现状态"""
        self.discovered = discovered

    def set_hidden(self, hidden):
        """设置隐藏状态"""
        self.hidden = hidden

    def set_target(self, target_scene=None, target_dialogue=None):
        """设置跳转目标"""
        self.target_scene = target_scene
        self.target_dialogue = target_dialogue
