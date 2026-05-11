"""
存档管理器
负责游戏状态和任务进度的保存、读取、查询。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from engine.game_state import get_game_state


class SaveManager:
    """存档管理器（单例）。"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.save_dir = Path(__file__).resolve().parent.parent / "saves"
        self.max_slots = 5
        self.save_dir.mkdir(exist_ok=True)
        print("[存档管理器] 初始化完成")

    def get_save_path(self, slot: int) -> Path:
        """获取存档文件路径。"""
        return self.save_dir / f"save_{slot}.json"

    def save_game(self, slot: int) -> bool:
        """保存游戏到指定槽位。"""
        if not self._is_valid_slot(slot):
            print(f"[存档管理器] 无效槽位: {slot}")
            return False

        try:
            save_data = self._build_save_data(slot)
            save_path = self.get_save_path(slot)
            with open(save_path, "w", encoding="utf-8") as file:
                json.dump(save_data, file, ensure_ascii=False, indent=2)

            print(f"[存档管理器] 保存游戏到槽位 {slot}: {save_path}")
            return True
        except Exception as exc:
            print(f"[存档管理器] 保存失败: {exc}")
            return False

    def load_game(self, slot: int) -> bool:
        """从指定槽位加载游戏。"""
        save_data = self.load_save_data(slot)
        if not save_data:
            return False

        try:
            game_state = get_game_state()
            state_data = save_data.get("game_state") or self._legacy_game_state(save_data)
            game_state.load_state(state_data)

            task_progress = save_data.get("task_progress")
            if task_progress is not None:
                self._get_task_manager().load_progress(task_progress)
            else:
                self._get_task_manager().reset_progress(game_state)

            print(f"[存档管理器] 加载游戏从槽位 {slot}")
            return True
        except Exception as exc:
            print(f"[存档管理器] 加载失败: {exc}")
            return False

    def load_latest_game(self) -> bool:
        """加载最近修改的存档。"""
        slot = self.get_latest_save_slot()
        if slot is None:
            print("[存档管理器] 没有可继续的存档")
            return False
        return self.load_game(slot)

    def load_save_data(self, slot: int) -> Optional[Dict[str, Any]]:
        """读取完整存档数据，但不应用到当前游戏。"""
        if not self._is_valid_slot(slot):
            return None

        save_path = self.get_save_path(slot)
        if not save_path.exists():
            print(f"[存档管理器] 存档不存在: {save_path}")
            return None

        try:
            with open(save_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, dict):
                print(f"[存档管理器] 存档格式无效: {save_path}")
                return None
            return data
        except Exception as exc:
            print(f"[存档管理器] 读取存档失败: {exc}")
            return None

    def delete_save(self, slot: int) -> bool:
        """删除指定槽位的存档。"""
        try:
            save_path = self.get_save_path(slot)
            if save_path.exists():
                save_path.unlink()
                print(f"[存档管理器] 删除存档: {save_path}")
                return True
            return False
        except Exception as exc:
            print(f"[存档管理器] 删除失败: {exc}")
            return False

    def get_save_info(self, slot: int) -> Dict[str, Any]:
        """获取存档摘要。"""
        if not self._is_valid_slot(slot) or not self.get_save_path(slot).exists():
            return {"exists": False}

        save_data = self.load_save_data(slot)
        if not save_data:
            return {"exists": False}

        game_state_data = save_data.get("game_state") or self._legacy_game_state(save_data)
        current_scene = game_state_data.get("current_scene", "unknown")
        task_progress = save_data.get("task_progress", {})
        current_task_id = task_progress.get("current_task_id")

        return {
            "exists": True,
            "timestamp": save_data.get("timestamp", ""),
            "playtime": save_data.get("playtime", ""),
            "slot": save_data.get("slot", slot),
            "current_scene": current_scene,
            "current_task_id": current_task_id,
        }

    def has_save(self, slot: int) -> bool:
        """检查指定槽位是否有存档。"""
        return self.get_save_path(slot).exists()

    def has_any_save(self) -> bool:
        """检查是否有任何存档。"""
        return self.get_latest_save_slot() is not None

    def get_latest_save_slot(self) -> Optional[int]:
        """获取最近修改的存档槽位。"""
        candidates = [
            (slot, self.get_save_path(slot))
            for slot in range(1, self.max_slots + 1)
            if self.get_save_path(slot).exists()
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item[1].stat().st_mtime)[0]

    def reset_for_new_game(self):
        """开始新游戏时清空内存状态和任务进度。"""
        game_state = get_game_state()
        game_state.reset()
        game_state.current_scene = "second_floor_hallway"
        self._get_task_manager().reset_progress(game_state)

    def _build_save_data(self, slot: int) -> Dict[str, Any]:
        game_state = get_game_state()
        return {
            "version": "1.1",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "playtime": self._get_playtime(),
            "slot": slot,
            "game_state": game_state.save_state(),
            "task_progress": self._get_task_manager().save_progress(),
        }

    def _get_task_manager(self):
        from engine.asset_manager import AssetManager
        from engine.task_manager import get_task_manager

        return get_task_manager(AssetManager())

    def _legacy_game_state(self, save_data: Dict[str, Any]) -> Dict[str, Any]:
        """兼容旧版 SaveSystem 直接平铺的存档格式。"""
        return {
            "game_time": save_data.get("game_time", {}),
            "variables": save_data.get("variables", {}),
            "player_stats": save_data.get("player_stats", {}),
            "npc_affections": save_data.get("npc_affections", {}),
            "flags": save_data.get("flags", []),
            "current_scene": save_data.get("current_scene", "second_floor_hallway"),
            "discovered_hotspots": save_data.get("discovered_hotspots", []),
        }

    def _is_valid_slot(self, slot: int) -> bool:
        return 1 <= int(slot) <= self.max_slots

    def _get_playtime(self) -> str:
        """获取游玩时间（占位）。"""
        return "00:00:00"


_save_manager = None


def get_save_manager() -> SaveManager:
    """获取存档管理器单例。"""
    global _save_manager
    if _save_manager is None:
        _save_manager = SaveManager()
    return _save_manager
