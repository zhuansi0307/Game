"""
任务系统模块

重写后的任务系统把“是否可触发”和“触发后是否渲染任务相关 UI”拆开处理：
- 任务是否可触发由前置任务、当前场景、玩家点击/热区、时间条件共同决定。
- 未解锁的任务热区不会交给 UI 渲染，也不会响应点击。
- 奖励由 RewardTask 统一发放，支持任务步骤奖励和任务完成奖励。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass
class TriggerContext:
    """一次任务触发检查的上下文。"""

    scene_id: str
    event_type: str = "scene_enter"
    hotspot_id: Optional[str] = None


@dataclass
class TaskStep:
    """任务步骤。"""

    step: int
    type: str
    dialogue_id: Optional[str] = None
    cutscene_id: Optional[str] = None
    target_scene: Optional[str] = None
    min_interactions: int = 0
    next_step: Optional[int] = None
    choices: List[Dict[str, Any]] = field(default_factory=list)
    wait_duration: float = 0.0
    description: str = ""
    guide: str = ""
    flags: Dict[str, Any] = field(default_factory=dict)
    reward: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    STEP_TYPES = {
        "dialogue",
        "cutscene",
        "scene_transition",
        "explore",
        "complete",
        "choice",
        "wait",
        "cutscene_arrive",
    }

    @classmethod
    def from_dict(cls, step_data: Dict[str, Any]) -> "TaskStep":
        reward = dict(step_data.get("reward") or step_data.get("rewards") or {})
        return cls(
            step=int(step_data.get("step", 0) or 0),
            type=step_data.get("type", ""),
            dialogue_id=step_data.get("dialogue_id"),
            cutscene_id=step_data.get("cutscene_id"),
            target_scene=step_data.get("target_scene"),
            min_interactions=int(step_data.get("min_interactions", 0) or 0),
            next_step=step_data.get("next_step"),
            choices=list(step_data.get("choices", [])),
            wait_duration=float(step_data.get("wait_duration", 0) or 0),
            description=step_data.get("description", ""),
            guide=step_data.get("guide", step_data.get("description", "")),
            flags=dict(step_data.get("flags", {})),
            reward=reward,
            raw=dict(step_data),
        )

    def reward_payload(self) -> Dict[str, Any]:
        """返回该步骤完成时需要发放的奖励。"""
        payload = dict(self.reward)
        if self.flags:
            flags = dict(payload.get("flags", {}))
            flags.update(self.flags)
            payload["flags"] = flags
        return payload


class RewardSystem:
    """任务奖励发放器。"""

    def apply(
        self,
        reward_data: Optional[Dict[str, Any]],
        game_state=None,
        tasks: Optional[Dict[str, "Task"]] = None,
    ) -> List[str]:
        if not reward_data:
            return []

        applied: List[str] = []

        if game_state:
            for flag_name, flag_value in dict(reward_data.get("flags", {})).items():
                if flag_value is False:
                    game_state.clear_flag(flag_name)
                    applied.append(f"clear_flag:{flag_name}")
                elif flag_value is True:
                    game_state.set_flag(flag_name)
                    applied.append(f"flag:{flag_name}")
                else:
                    game_state.set_variable(flag_name, flag_value)
                    applied.append(f"variable:{flag_name}")

            for name, value in dict(reward_data.get("variables", {})).items():
                game_state.set_variable(name, value)
                applied.append(f"variable:{name}")

            for name, amount in dict(reward_data.get("player_stats", {})).items():
                game_state.add_player_stat(name, amount)
                applied.append(f"player_stat:{name}")

            time_period = reward_data.get("time_period")
            if time_period:
                game_state.game_time.set_period(time_period)
                applied.append(f"time_period:{time_period}")

            game_day = reward_data.get("game_day")
            if game_day:
                game_state.game_time.set_time(
                    int(game_day),
                    game_state.game_time.get_period_index(),
                )
                applied.append(f"game_day:{game_day}")

            for npc_id, amount in dict(reward_data.get("npc_affections", {})).items():
                game_state.add_npc_affection(npc_id, amount)
                applied.append(f"npc_affection:{npc_id}")

            for hotspot_id in reward_data.get("discover_hotspots", []):
                game_state.discovered_hotspots.add(hotspot_id)
                applied.append(f"discover_hotspot:{hotspot_id}")

        unlock_ids: List[str] = []
        unlock_task = reward_data.get("unlock_task")
        if unlock_task:
            unlock_ids.append(unlock_task)
        unlock_ids.extend(reward_data.get("unlock_tasks", []))

        if tasks:
            for task_id in unlock_ids:
                task = tasks.get(task_id)
                if task and task.status == Task.STATUS["locked"]:
                    task.status = Task.STATUS["available"]
                    applied.append(f"unlock_task:{task_id}")

        return applied


class Task:
    """任务基类。"""

    STATUS = {
        "locked": "locked",
        "available": "available",
        "in_progress": "in_progress",
        "completed": "completed",
        "failed": "failed",
    }

    def __init__(self, task_data: Dict[str, Any]):
        self.raw = dict(task_data)
        self.id = task_data.get("id", "")
        self.title = task_data.get("title", self.id)
        self.description = task_data.get("description", "")
        self.chapter = int(task_data.get("chapter", 0) or 0)
        self.display_order = int(task_data.get("display_order", 0) or 0)
        self.repeatable = bool(task_data.get("repeatable", False))
        self.guide = task_data.get("guide", self.description)

        self.trigger: Dict[str, Any] = dict(task_data.get("trigger", {}))
        self.prerequisites: List[str] = self._collect_prerequisites(task_data)
        self.steps: List[TaskStep] = [
            TaskStep.from_dict(step) for step in task_data.get("steps", [])
        ]
        self.completion_reward: Dict[str, Any] = dict(
            task_data.get("completion_reward", {})
        )

        self.status = self.STATUS["locked"]
        self.current_step_index = 0
        self.started_at = None
        self.completed_at = None

    def _collect_prerequisites(self, task_data: Dict[str, Any]) -> List[str]:
        prerequisites = list(task_data.get("prerequisites", []))
        for key in ("previous_task", "previous_task_id", "after_task"):
            value = task_data.get(key) or self.trigger.get(key)
            if value and value not in prerequisites:
                prerequisites.append(value)
        return prerequisites

    def can_unlock(self, manager: "TaskManager", game_state) -> bool:
        return all(manager.is_task_completed(task_id, game_state) for task_id in self.prerequisites)

    def can_start(self, manager: "TaskManager", game_state) -> bool:
        if self.status == self.STATUS["locked"] and self.can_unlock(manager, game_state):
            self.status = self.STATUS["available"]

        if self.status == self.STATUS["available"]:
            return True

        if self.repeatable and self.status == self.STATUS["completed"]:
            return self.can_unlock(manager, game_state)

        return False

    def start(self):
        self.status = self.STATUS["in_progress"]
        self.current_step_index = 0
        self.started_at = True
        self.completed_at = None
        print(f"[任务系统] 开始任务: {self.title}")

    def complete(self):
        self.status = self.STATUS["completed"]
        self.completed_at = True
        print(f"[任务系统] 完成任务: {self.title}")

    def get_current_step(self) -> Optional[TaskStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def advance_from(self, step: TaskStep, game_state=None) -> Optional[TaskStep]:
        next_step = step.next_step
        if step.type in {"choice", "chooser"}:
            branch_step = self._resolve_choice_next_step(step, game_state)
            if branch_step is not None:
                next_step = branch_step

        if next_step is not None:
            next_index = int(next_step) - 1
        else:
            next_index = self.current_step_index + 1

        self.current_step_index = next_index
        return self.get_current_step()

    def _resolve_choice_next_step(self, step: TaskStep, game_state=None):
        if not game_state:
            return None

        action = game_state.get_variable("last_choice_result")
        if action is None:
            return None

        action_text = str(action)
        for choice in step.choices:
            aliases = [
                choice.get("action"),
                choice.get("id"),
                choice.get("label"),
                choice.get("text"),
            ]
            if action_text in {str(alias) for alias in aliases if alias is not None}:
                return choice.get("next_step") or choice.get("target_step")
        return None

    def matches_trigger(
        self,
        context: TriggerContext,
        game_state,
        manager: "TaskManager",
        ignore_hotspot: bool = False,
    ) -> bool:
        if not self._matches_previous_tasks(manager, game_state):
            return False

        trigger = self.trigger
        trigger_type = trigger.get("condition_type")
        if not trigger_type:
            trigger_type = "scene_hotspot" if trigger.get("hotspot_id") else "scene_only"

        if trigger_type in {"manual", "none"}:
            return False

        if not self._matches_scene(context.scene_id):
            return False
        if not self._matches_time(game_state):
            return False
        if not self._matches_click_count(game_state):
            return False
        if not self._matches_extra_conditions(game_state):
            return False

        required_hotspot = trigger.get("hotspot_id")
        if required_hotspot and not ignore_hotspot:
            if context.event_type != "hotspot_click":
                return False
            if context.hotspot_id != required_hotspot:
                return False

        if ignore_hotspot and trigger_type in {"scene_hotspot", "hotspot_click"}:
            return True

        if trigger_type in {"scene_hotspot", "hotspot_click"} and not ignore_hotspot:
            return context.event_type == "hotspot_click"

        if trigger_type in {"scene_only", "time_scene", "game_day"}:
            return context.event_type == "scene_enter"

        if trigger_type == "full":
            return context.event_type == "hotspot_click" if required_hotspot else True

        if trigger_type == "always":
            return True

        return False

    def _matches_previous_tasks(self, manager: "TaskManager", game_state) -> bool:
        for task_id in self.prerequisites:
            if not manager.is_task_completed(task_id, game_state):
                return False
        return True

    def _matches_scene(self, scene_id: str) -> bool:
        required_scene = self.trigger.get("scene")
        return not required_scene or required_scene == scene_id

    def _matches_time(self, game_state) -> bool:
        required_day = self.trigger.get("game_day")
        required_period = self.trigger.get("period")
        return (
            game_state.game_time.is_game_day_match(required_day)
            and game_state.game_time.is_period_match(required_period)
        )

    def _matches_click_count(self, game_state) -> bool:
        min_clicks = (
            self.trigger.get("min_clicks")
            or self.trigger.get("click_count")
            or self.trigger.get("min_interactions")
        )
        if min_clicks is None:
            return True
        return game_state.game_time.get_click_count() >= int(min_clicks)

    def _matches_extra_conditions(self, game_state) -> bool:
        conditions = self.trigger.get("conditions", [])
        if isinstance(conditions, dict):
            conditions = [conditions]
        return all(game_state.check_condition(condition) for condition in conditions)


class RewardTask(Task):
    """带奖励发放能力的任务。"""

    def __init__(self, task_data: Dict[str, Any], reward_system: RewardSystem):
        super().__init__(task_data)
        self.reward_system = reward_system

    def apply_step_reward(
        self,
        step: TaskStep,
        game_state=None,
        tasks: Optional[Dict[str, Task]] = None,
    ) -> List[str]:
        return self.reward_system.apply(step.reward_payload(), game_state, tasks)

    def apply_completion_reward(
        self,
        game_state=None,
        tasks: Optional[Dict[str, Task]] = None,
    ) -> List[str]:
        return self.reward_system.apply(self.completion_reward, game_state, tasks)


class TaskManager:
    """任务管理器。"""

    def __init__(self, asset_manager):
        self.asset_manager = asset_manager
        self.tasks_data = asset_manager.load_tasks()
        self.reward_system = RewardSystem()
        self.tasks: Dict[str, RewardTask] = {}
        self.current_task_id: Optional[str] = None
        self.task_notifications: List[Dict[str, Any]] = []
        self.task_ui = None
        self.last_guidance: Optional[Dict[str, str]] = None
        self.hotspot_triggers: Dict[Tuple[str, str], List[str]] = {}

        self._load_tasks()

    def _load_tasks(self):
        self.tasks.clear()
        for task_data in self.tasks_data.get("tasks", []):
            task = RewardTask(task_data, self.reward_system)
            if not task.id:
                continue
            self.tasks[task.id] = task

        self._index_hotspot_triggers()
        print(f"[任务系统] 加载了 {len(self.tasks)} 个任务")

    def _index_hotspot_triggers(self):
        self.hotspot_triggers.clear()
        for task in self.tasks.values():
            scene_id = task.trigger.get("scene")
            hotspot_id = task.trigger.get("hotspot_id")
            if scene_id and hotspot_id:
                self.hotspot_triggers.setdefault((scene_id, hotspot_id), []).append(task.id)

    def bind_ui(self, task_ui):
        self.task_ui = task_ui
        self._sync_ui()

    def check_and_trigger_task(
        self,
        scene_id: str,
        game_state,
        hotspot_id: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> Optional[RewardTask]:
        if not self.tasks_data.get("task_globals", {}).get("auto_check_trigger", True):
            return None

        self.update_task_availability(game_state)
        if self.get_current_task():
            self._sync_ui()
            return None

        context = TriggerContext(
            scene_id=scene_id,
            hotspot_id=hotspot_id,
            event_type=event_type or ("hotspot_click" if hotspot_id else "scene_enter"),
        )

        for task in self._ordered_tasks():
            if task.can_start(self, game_state) and task.matches_trigger(context, game_state, self):
                task.start()
                self.current_task_id = task.id
                self._show_notification(f"新任务：{task.title}")
                self._sync_ui()
                return task

        self._sync_ui()
        return None

    def update_task_availability(self, game_state):
        for task in self._ordered_tasks():
            if game_state and self.is_task_completed(task.id, game_state) and not task.repeatable:
                task.status = Task.STATUS["completed"]
                continue
            if task.status == Task.STATUS["locked"] and task.can_unlock(self, game_state):
                task.status = Task.STATUS["available"]
        self._sync_ui()

    def is_task_completed(self, task_id: str, game_state=None) -> bool:
        task = self.tasks.get(task_id)
        if task and task.status == Task.STATUS["completed"]:
            return True

        if not game_state:
            return False

        for flag_name in self._completion_flag_candidates(task_id):
            if game_state.check_flag(flag_name):
                return True
        return False

    def _completion_flag_candidates(self, task_id: str) -> Iterable[str]:
        yield f"{task_id}_completed"
        if task_id.startswith("task_"):
            yield f"{task_id[len('task_'):]}_completed"
        else:
            yield f"task_{task_id}_completed"

    def get_current_task(self) -> Optional[RewardTask]:
        if not self.current_task_id:
            return None
        task = self.tasks.get(self.current_task_id)
        if task and task.status == Task.STATUS["in_progress"]:
            return task
        return None

    def advance_current_task(self, game_state=None) -> Optional[TaskStep]:
        task = self.get_current_task()
        if not task:
            self._sync_ui()
            return None

        current_step = task.get_current_step()
        if not current_step:
            self._complete_task(task, game_state)
            return None

        task.apply_step_reward(current_step, game_state, self.tasks)

        if current_step.type == "complete":
            self._complete_task(task, game_state)
            return None

        next_step = task.advance_from(current_step, game_state)
        if not next_step:
            self._complete_task(task, game_state)
            return None

        self._sync_ui()
        return next_step

    def _complete_task(self, task: RewardTask, game_state=None):
        task.complete()
        task.apply_completion_reward(game_state, self.tasks)
        self.current_task_id = None
        self.last_guidance = None
        self.update_task_availability(game_state)
        self._show_notification(f"任务完成：{task.title}")
        self._sync_ui()

    def skip_current_step(self):
        return self.advance_current_task()

    def should_render_hotspot_ui(
        self,
        scene_id: str,
        hotspot_id: str,
        game_state,
        has_default_navigation: bool = False,
    ) -> bool:
        """普通跳转热区一直渲染；纯任务热区未解锁时不渲染。"""
        if has_default_navigation:
            return True

        task_ids = self.hotspot_triggers.get((scene_id, hotspot_id), [])
        if not task_ids:
            return True

        context = TriggerContext(
            scene_id=scene_id,
            hotspot_id=hotspot_id,
            event_type="hotspot_click",
        )

        for task_id in task_ids:
            task = self.tasks.get(task_id)
            if not task:
                continue
            if task.status == Task.STATUS["completed"] and not task.repeatable:
                continue
            if task.can_start(self, game_state) and task.matches_trigger(
                context,
                game_state,
                self,
                ignore_hotspot=True,
            ):
                return True

        return False

    def should_render_task_ui(self) -> bool:
        return bool(self.get_current_task() or self.task_notifications)

    def get_task_by_id(self, task_id: str) -> Optional[RewardTask]:
        return self.tasks.get(task_id)

    def get_tasks_by_status(self, status: str) -> List[RewardTask]:
        return [task for task in self._ordered_tasks() if task.status == status]

    def get_active_tasks(self) -> List[RewardTask]:
        return self.get_tasks_by_status(Task.STATUS["in_progress"])

    def get_available_tasks(self) -> List[RewardTask]:
        return self.get_tasks_by_status(Task.STATUS["available"])

    def _ordered_tasks(self) -> List[RewardTask]:
        return sorted(self.tasks.values(), key=lambda task: (task.display_order, task.id))

    def _show_notification(self, message: str):
        duration = self.tasks_data.get("task_globals", {}).get("notification_duration", 3.0)
        notification = {"message": message, "duration": duration, "elapsed": 0.0}
        self.task_notifications.append(notification)

        if self.task_ui and self.tasks_data.get("task_globals", {}).get("show_notification", True):
            self.task_ui.show_notification(message, duration)

    def update_notifications(self, dt: float):
        for notification in self.task_notifications[:]:
            notification["elapsed"] += dt
            if notification["elapsed"] >= notification["duration"]:
                self.task_notifications.remove(notification)

    def get_notifications(self) -> List[Dict[str, Any]]:
        return list(self.task_notifications)

    def get_guidance(self, scene_id: str, game_state=None) -> Optional[Dict[str, str]]:
        """获取当前任务引导信息，供 UI 渲染。"""
        current = self.get_current_task()
        if current:
            step = current.get_current_step()
            hint = ""
            if step:
                hint = step.guide or step.description or self._step_fallback_hint(step)
            return self._remember_guidance({
                "title": current.title,
                "hint": hint or current.guide or current.description,
                "status": "进行中",
            })

        if game_state:
            self.update_task_availability(game_state)

        scene_tasks = [
            task for task in self._ordered_tasks()
            if task.trigger.get("scene") == scene_id
            and self._can_show_available_guidance(task, scene_id, game_state)
        ]
        if scene_tasks:
            task = scene_tasks[0]
            hotspot_id = task.trigger.get("hotspot_id")
            hint = task.guide or task.description
            if hotspot_id:
                hint = hint or f"点击热区 {hotspot_id}"
            return self._remember_guidance({"title": task.title, "hint": hint, "status": "可接取"})

        available = [
            task for task in self._ordered_tasks()
            if self._can_show_available_guidance(
                task,
                task.trigger.get("scene") or scene_id,
                game_state,
            )
        ]
        if available:
            task = available[0]
            target_scene = task.trigger.get("scene")
            hint = task.guide or task.description
            if target_scene and target_scene != scene_id:
                hint = hint or f"前往 {target_scene}"
            return self._remember_guidance({"title": task.title, "hint": hint, "status": "可接取"})

        return self.last_guidance

    def _remember_guidance(self, guidance: Dict[str, str]) -> Dict[str, str]:
        self.last_guidance = guidance
        return guidance

    def _can_show_available_guidance(self, task: RewardTask, scene_id: str, game_state=None) -> bool:
        if not game_state:
            return task.status == Task.STATUS["available"]

        hotspot_id = task.trigger.get("hotspot_id")
        context = TriggerContext(
            scene_id=scene_id,
            hotspot_id=hotspot_id,
            event_type="hotspot_click" if hotspot_id else "scene_enter",
        )
        return task.can_start(self, game_state) and task.matches_trigger(
            context,
            game_state,
            self,
            ignore_hotspot=bool(hotspot_id),
        )

    def _step_fallback_hint(self, step: TaskStep) -> str:
        if step.type == "cutscene":
            return "观看剧情播片"
        if step.type == "choice":
            return "做出选择"
        if step.type == "scene_transition" and step.target_scene:
            return f"前往 {step.target_scene}"
        if step.type == "complete":
            return "完成任务"
        return ""

    def _sync_ui(self):
        if not self.task_ui:
            return
        current_task = self.get_current_task()
        if current_task:
            self.task_ui.set_current_task(current_task)
        else:
            self.task_ui.clear_current_task()

    def save_progress(self) -> Dict[str, Any]:
        progress = {}
        for task_id, task in self.tasks.items():
            progress[task_id] = {
                "status": task.status,
                "current_step_index": task.current_step_index,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
            }
        return {
            "current_task_id": self.current_task_id,
            "tasks_progress": progress,
        }

    def load_progress(self, data: Dict[str, Any]):
        self.current_task_id = data.get("current_task_id")
        self.last_guidance = None
        for task_id, task_data in data.get("tasks_progress", {}).items():
            task = self.tasks.get(task_id)
            if not task:
                continue
            task.status = task_data.get("status", Task.STATUS["locked"])
            task.current_step_index = int(task_data.get("current_step_index", 0) or 0)
            task.started_at = task_data.get("started_at")
            task.completed_at = task_data.get("completed_at")
        self._sync_ui()

    def reset_progress(self, game_state=None):
        """重置所有任务进度，用于开始新游戏。"""
        self.current_task_id = None
        self.last_guidance = None
        self.task_notifications.clear()
        for task in self.tasks.values():
            task.status = Task.STATUS["locked"]
            task.current_step_index = 0
            task.started_at = None
            task.completed_at = None

        if game_state:
            self.update_task_availability(game_state)
        self._sync_ui()


def get_task_manager(asset_manager) -> TaskManager:
    """获取任务管理器单例。"""
    if not hasattr(get_task_manager, "_instance"):
        get_task_manager._instance = TaskManager(asset_manager)
    return get_task_manager._instance
