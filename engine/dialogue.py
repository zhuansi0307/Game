"""
对话系统模块
负责加载和管理游戏对话，提供对话推进功能
"""

import json
from pathlib import Path


class DialogueRunner:
    """
    对话运行器
    用于管理和播放游戏对话
    """

    def __init__(self, asset_manager):
        """
        初始化对话运行器
        :param asset_manager: 资源管理器实例
        """
        self.asset_manager = asset_manager
        self.dialogues = asset_manager.load_dialogues()

        # 当前对话状态
        self.current_dialogue_id = None
        self.current_index = 0
        self.lines = []

    def start(self, dialogue_id):
        """
        开始一段对话
        :param dialogue_id: 对话ID（对应 dialogues.json 中的键）
        :return: bool 是否成功开始
        """
        if dialogue_id not in self.dialogues:
            print(f"[错误] 对话 {dialogue_id} 不存在!")
            return False

        self.current_dialogue_id = dialogue_id
        self.lines = self.dialogues[dialogue_id]
        self.current_index = 0

        print(f"[对话系统] 开始对话: {dialogue_id}")
        return True

    def current_line(self):
        """
        获取当前对话行
        :return: dict 包含 speaker 和 text，如果对话结束返回 None
        """
        if self.current_index >= len(self.lines):
            return None
        return self.lines[self.current_index]

    def next(self):
        """
        推进到下一行对话
        :return: bool 是否成功推进（还有下一行返回True）
        """
        if self.current_index < len(self.lines) - 1:
            self.current_index += 1
            return True
        return False

    def is_finished(self):
        """
        检查对话是否结束
        :return: bool
        """
        return self.current_index >= len(self.lines)

    def get_progress(self):
        """
        获取对话进度
        :return: tuple (current_index, total_lines)
        """
        return (self.current_index + 1, len(self.lines))

    def reset(self):
        """重置对话状态"""
        self.current_dialogue_id = None
        self.current_index = 0
        self.lines = []

    def reload_dialogues(self):
        """重新加载对话数据"""
        self.dialogues = self.asset_manager.load_dialogues()
        # 如果当前有对话在播放，重新加载
        if self.current_dialogue_id and self.current_dialogue_id in self.dialogues:
            self.lines = self.dialogues[self.current_dialogue_id]


class DialogueChoice:
    """
    对话选项（可选扩展）
    """

    def __init__(self, text, target_scene=None, variables=None):
        """
        初始化对话选项
        :param text: 选项文本
        :param target_scene: 选择后的目标场景
        :param variables: 选择后设置的变量
        """
        self.text = text
        self.target_scene = target_scene
        self.variables = variables or {}