"""
游戏全局状态管理模块
负责管理游戏时间、进度、变量等全局状态
"""

import json
from pathlib import Path


class GameTime:
    """游戏时间系统"""

    WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday"]

    TIME_PERIODS = ["morning", "noon", "afternoon", "evening"]

    TIME_DISPLAY_CN = {
        "morning": "早上",
        "noon": "中午",
        "afternoon": "下午",
        "evening": "晚上"
    }

    TIME_DISPLAY_EN = {
        "morning": "Morning",
        "noon": "Noon",
        "afternoon": "Afternoon",
        "evening": "Evening"
    }

    def __init__(self):
        self.day_number = 1
        self.period = 0
        self.weekday_index = 0
        self.click_count = 0
        self.clicks_per_period = 3

    def get_click_count(self) -> int:
        """获取当前点击计数"""
        return self.click_count

    def add_click(self):
        """添加一次点击，用于时间推进"""
        self.click_count += 1
        # TODO: 推进时段的判定方式暂时空置，待后续实现
        # if self.click_count >= self.clicks_per_period:
        #     self._advance_period()
        #     self.click_count = 0
        #     print(f"[时间系统] 时间推进到: {self.get_display_text()}")

    def _advance_period(self):
        """推进时间段"""
        self.period += 1
        if self.period > 3:
            self.period = 0
            self.day_number += 1
        self.weekday_index = (self.day_number - 1) % 7

    def set_period(self, period_name):
        """直接设置时段"""
        if period_name in self.TIME_PERIODS:
            self.period = self.TIME_PERIODS.index(period_name)
            self.weekday_index = (self.day_number - 1) % 7

    def rewind_day(self):
        """回溯到前一天（同一时段）"""
        if self.day_number > 1:
            self.day_number -= 1
            self.weekday_index = (self.day_number - 1) % 7
            print(f"[时间回溯] 回到: {self.get_display_text()}")
            return True
        return False

    def can_rewind(self) -> bool:
        """检查是否可以回溯"""
        return self.day_number > 1

    def get_game_day(self) -> int:
        """获取游戏第几天"""
        return self.day_number

    def get_period_index(self) -> int:
        """获取时间段索引"""
        return self.period

    def get_period_name(self) -> str:
        """获取时间段名称"""
        return self.TIME_PERIODS[self.period]

    def get_full_time_key(self) -> str:
        """获取完整时间键，如 'day3_afternoon'"""
        return f"day{self.day_number}_{self.get_period_name()}"

    def get_weekday(self) -> str:
        """获取星期几（用于显示）"""
        return self.WEEKDAYS[self.weekday_index]

    def get_display_text(self, lang="cn") -> str:
        """获取显示文本"""
        if lang == "cn":
            period_text = self.TIME_DISPLAY_CN.get(self.get_period_name(), self.get_period_name())
            return f"第{self.day_number}天 {period_text}"
        else:
            period_text = self.TIME_DISPLAY_EN.get(self.get_period_name(), self.get_period_name())
            return f"Day {self.day_number} {period_text}"

    def set_time(self, game_day: int, period_index: int):
        """设置游戏天数和时间段"""
        self.day_number = max(1, game_day)
        self.period = period_index % 4
        self.weekday_index = (game_day - 1) % 7
        self.click_count = 0

    def reset(self):
        """重置时间到第1天早上"""
        self.day_number = 1
        self.period = 0
        self.weekday_index = 0
        self.click_count = 0

    def is_game_day_match(self, required_day) -> bool:
        """检查游戏天数是否匹配"""
        if required_day is None:
            return True
        return self.day_number == required_day

    def is_period_match(self, required_period: str) -> bool:
        """检查时间段是否匹配"""
        if not required_period:
            return True
        return self.get_period_name() == required_period


class GameState:
    """
    游戏全局状态管理器（单例）
    """
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

        self.game_time = GameTime()
        self.variables = {}  # 自定义游戏变量
        self.player_stats = {"intelligence": 0, "stamina": 100, "money": 0}  # 主角属性
        self.npc_affections = {}  # NPC好感度
        self.flags = set()  # 事件标记
        self.current_scene = "main_menu"
        self.discovered_hotspots = set()

    def next_time_period(self):
        """推进时间到下一个时段"""
        self.game_time._advance_period()
        return self.game_time.get_full_time_key()

    def rewind_time(self):
        """回溯时间到前一天"""
        return self.game_time.rewind_day()

    def add_click(self):
        """添加一次点击"""
        self.game_time.add_click()

    def check_condition(self, condition):
        """检查条件是否满足"""
        if not condition:
            return True

        if "game_day" in condition:
            if not self.game_time.is_game_day_match(condition["game_day"]):
                return False

        if "period" in condition:
            if not self.game_time.is_period_match(condition["period"]):
                return False

        if "flag" in condition:
            if condition["flag"] not in self.flags:
                return False

        if "not_flag" in condition:
            if condition["not_flag"] in self.flags:
                return False

        if "variable" in condition:
            var_name = condition["variable"]
            expected = condition.get("value")
            if var_name not in self.variables:
                return False
            if expected is not None and self.variables[var_name] != expected:
                return False

        if "player_stat" in condition:
            stat_name = condition["player_stat"]
            expected = condition.get("value")
            min_val = condition.get("min")
            max_val = condition.get("max")
            actual = self.get_player_stat(stat_name)

            if expected is not None and actual != expected:
                return False
            if min_val is not None and actual < min_val:
                return False
            if max_val is not None and actual > max_val:
                return False

        if "npc_affection" in condition:
            npc_id = condition["npc_affection"]
            expected = condition.get("value")
            min_val = condition.get("min")
            max_val = condition.get("max")
            actual = self.get_npc_affection(npc_id)

            if expected is not None and actual != expected:
                return False
            if min_val is not None and actual < min_val:
                return False
            if max_val is not None and actual > max_val:
                return False

        return True

    def get_player_stat(self, stat_name: str, default=0) -> int:
        """获取主角属性"""
        return self.player_stats.get(stat_name, default)

    def set_player_stat(self, stat_name: str, value: int):
        """设置主角属性"""
        self.player_stats[stat_name] = value

    def add_player_stat(self, stat_name: str, amount: int):
        """增加/减少主角属性"""
        current = self.get_player_stat(stat_name)
        self.player_stats[stat_name] = current + amount

    def get_npc_affection(self, npc_id: str, default=0) -> int:
        """获取NPC好感度 (0-100)"""
        return self.npc_affections.get(npc_id, default)

    def set_npc_affection(self, npc_id: str, value: int):
        """设置NPC好感度 (限制在0-100之间)"""
        self.npc_affections[npc_id] = max(0, min(100, value))

    def add_npc_affection(self, npc_id: str, amount: int):
        """增加/减少NPC好感度 (限制在0-100之间)"""
        current = self.get_npc_affection(npc_id)
        self.set_npc_affection(npc_id, current + amount)

    def set_variable(self, name, value):
        """设置游戏变量"""
        self.variables[name] = value

    def get_variable(self, name, default=None):
        """获取游戏变量"""
        return self.variables.get(name, default)

    def set_flag(self, flag, value=True):
        """设置事件标记，支持单个标志或字典形式"""
        if isinstance(flag, dict):
            for k, v in flag.items():
                flag_key = k if v is True else f"{k}={v}"
                self.flags.add(flag_key)
        else:
            self.flags.add(flag)

    def check_flag(self, flag):
        """检查是否有标记"""
        return flag in self.flags

    def has_flag(self, flag):
        """检查是否有标记"""
        return flag in self.flags

    def clear_flag(self, flag):
        """清除事件标记"""
        self.flags.discard(flag)

    def save_state(self):
        """获取存档用的状态数据"""
        return {
            "game_time": {
                "day_number": self.game_time.day_number,
                "period": self.game_time.period,
                "click_count": self.game_time.click_count
            },
            "variables": self.variables,
            "player_stats": self.player_stats,
            "npc_affections": self.npc_affections,
            "flags": list(self.flags),
            "current_scene": self.current_scene,
            "discovered_hotspots": list(self.discovered_hotspots)
        }

    def load_state(self, data):
        """加载存档状态"""
        if "game_time" in data:
            gt = data["game_time"]
            self.game_time.day_number = gt.get("day_number", 1)
            self.game_time.period = gt.get("period", 0)
            self.game_time.click_count = gt.get("click_count", 0)
            self.game_time.weekday_index = (self.game_time.day_number - 1) % 7

        if "variables" in data:
            self.variables = data["variables"]

        if "player_stats" in data:
            self.player_stats = data["player_stats"]

        if "npc_affections" in data:
            self.npc_affections = data["npc_affections"]

        if "flags" in data:
            self.flags = set(data["flags"])

        if "current_scene" in data:
            self.current_scene = data["current_scene"]

        if "discovered_hotspots" in data:
            self.discovered_hotspots = set(data["discovered_hotspots"])

    def reset(self):
        """重置游戏状态"""
        self.game_time = GameTime()
        self.variables = {}
        self.player_stats = {"intelligence": 0, "stamina": 100, "money": 0}
        self.npc_affections = {}
        self.flags = set()
        self.current_scene = "main_menu"
        self.discovered_hotspots = set()


def get_game_state():
    """获取游戏状态单例"""
    return GameState()
