"""
存档系统模块
提供简单的JSON格式存档功能
"""

import json
from pathlib import Path


class SaveSystem:
    """
    存档系统
    负责游戏的保存和加载功能
    """

    def __init__(self):
        # 保存目录
        self.save_dir = Path(__file__).resolve().parent.parent / "saves"
        self.save_dir.mkdir(exist_ok=True)

    def get_save_path(self, slot):
        """
        获取指定存档槽的保存路径
        :param slot: 存档槽编号 (0, 1, 2, ...)
        :return: Path 保存文件路径
        """
        return self.save_dir / f"save_{slot}.json"

    def save_game(self, slot, data):
        """
        保存游戏
        :param slot: 存档槽编号
        :param data: 要保存的数据字典
        :return: bool 是否保存成功
        """
        save_path = self.get_save_path(slot)

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[存档系统] 已保存到槽位 {slot}")
            return True
        except Exception as e:
            print(f"[错误] 保存失败: {e}")
            return False

    def load_game(self, slot):
        """
        加载游戏
        :param slot: 存档槽编号
        :return: dict 加载的数据，如果加载失败返回 None
        """
        save_path = self.get_save_path(slot)

        if not save_path.exists():
            print(f"[存档系统] 槽位 {slot} 没有存档")
            return None

        try:
            with open(save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"[存档系统] 已从槽位 {slot} 加载")
            return data
        except Exception as e:
            print(f"[错误] 加载失败: {e}")
            return None

    def has_save(self, slot):
        """
        检查指定槽位是否有存档
        :param slot: 存档槽编号
        :return: bool
        """
        return self.get_save_path(slot).exists()

    def delete_save(self, slot):
        """
        删除存档
        :param slot: 存档槽编号
        :return: bool 是否删除成功
        """
        save_path = self.get_save_path(slot)

        if not save_path.exists():
            return False

        try:
            save_path.unlink()
            print(f"[存档系统] 已删除槽位 {slot} 的存档")
            return True
        except Exception as e:
            print(f"[错误] 删除失败: {e}")
            return False

    def get_save_info(self, slot):
        """
        获取存档信息（不加载完整数据）
        :param slot: 存档槽编号
        :return: dict 包含基本信息的字典
        """
        data = self.load_game(slot)
        if data:
            return {
                "slot": slot,
                "scene": data.get("current_scene", "未知"),
                "timestamp": data.get("timestamp", 0),
                "playtime": data.get("playtime", "00:00:00")
            }
        return None

    @staticmethod
    def create_save_data(current_scene, discovered_hotspots=None, variables=None):
        """
        创建存档数据的标准格式
        :param current_scene: 当前场景名称
        :param discovered_hotspots: 已发现的热区列表
        :param variables: 游戏变量字典
        :return: dict 标准格式的存档数据
        """
        from datetime import datetime
        import time

        return {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "playtime": "00:00:00",  # TODO: 实现游戏时间追踪
            "current_scene": current_scene,
            "discovered_hotspots": discovered_hotspots or [],
            "variables": variables or {},
        }