"""
时间系统辅助函数
提供时间相关的检查和转换工具
"""

from .game_state import GameTime, get_game_state


TIME_PERIOD_ORDER = {
    "morning": 0,
    "noon": 1,
    "afternoon": 2,
    "evening": 3
}

WEEKDAY_ORDER = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}


def is_time_in_range(time_key, start_key, end_key):
    """
    检查时间是否在范围内（支持跨天）
    :param time_key: 当前时间，如 'Monday_evening'
    :param start_key: 开始时间，如 'Monday_noon'
    :param end_key: 结束时间，如 'Tuesday_morning'
    :return: bool
    """
    time_order = get_time_order(time_key)
    start_order = get_time_order(start_key)
    end_order = get_time_order(end_key)

    if end_order >= start_order:
        return start_order <= time_order <= end_order
    else:
        return time_order >= start_order or time_order <= end_order


def get_time_order(time_key):
    """
    将时间键转换为数值顺序
    :param time_key: 如 'Monday_evening'
    :return: 0-27 的整数
    """
    parts = time_key.split("_")
    if len(parts) != 2:
        return 0
    
    day = WEEKDAY_ORDER.get(parts[0], 0)
    period = TIME_PERIOD_ORDER.get(parts[1], 0)
    
    return day * 4 + period


def is_period(period_name):
    """检查当前是否是指定时段"""
    gs = get_game_state()
    return gs.game_time.get_period_name() == period_name


def is_weekday(weekday_name):
    """检查当前是否是指定星期"""
    gs = get_game_state()
    return gs.game_time.get_weekday() == weekday_name


def is_monday():
    return is_weekday("Monday")


def is_friday():
    return is_weekday("Friday")


def is_weekend():
    return is_weekday("Saturday") or is_weekday("Sunday")


def is_morning():
    return is_period("morning")


def is_evening():
    return is_period("evening")


def get_time_period_index(period_name):
    """获取时段索引"""
    return TIME_PERIOD_ORDER.get(period_name, 0)


def get_weekday_index(weekday_name):
    """获取星期索引"""
    return WEEKDAY_ORDER.get(weekday_name, 0)


def get_next_period(current_period):
    """获取下一个时段"""
    order = get_time_period_index(current_period)
    periods = list(TIME_PERIOD_ORDER.keys())
    return periods[(order + 1) % len(periods)]


def get_prev_period(current_period):
    """获取上一个时段"""
    order = get_time_period_index(current_period)
    periods = list(TIME_PERIOD_ORDER.keys())
    return periods[(order - 1) % len(periods)]


def format_time_display(day_index, period_index, lang="cn"):
    """格式化时间显示"""
    weekdays_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    periods_cn = ["早上", "中午", "下午", "晚上"]
    
    weekdays_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    periods_en = ["Morning", "Noon", "Afternoon", "Evening"]
    
    if lang == "cn":
        return f"{weekdays_cn[day_index]} {periods_cn[period_index]}"
    else:
        return f"{weekdays_en[day_index]} {periods_en[period_index]}"


def time_to_scene_key(time_key):
    """时间键转场景后缀，如 'Monday_noon' -> 'monday_noon'"""
    parts = time_key.split("_")
    if len(parts) == 2:
        return f"{parts[0].lower()}_{parts[1]}"
    return time_key.lower()