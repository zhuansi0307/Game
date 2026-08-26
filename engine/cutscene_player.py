"""
播片系统模块

播片条目被建模为 CutsceneTask(Task)，即任务系统的一个子类。
CutscenePlayer 只负责播放、seek、缓冲、画面帧和音频同步，不再承担任务推进职责。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import pygame

from .constants import SCREEN_HEIGHT, SCREEN_WIDTH, COLOR_BG_DARK, COLOR_CHAMPAGNE, COLOR_TEXT
from .task_manager import Task
from .video_frame_reader import VideoFrameReader


class PlaybackState(Enum):
    """播放状态。"""

    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    FINISHED = "finished"


@dataclass
class CutsceneFrame:
    """图片播片帧。"""

    image: str
    duration: float = 2.0
    dialogue: Optional[Dict] = None


class CutsceneTask(Task):
    """播片任务，是任务系统 Task 的子类。"""

    TYPE_VIDEO = "video"
    TYPE_IMAGE = "image"

    def __init__(self, cutscene_data: Dict, asset_manager):
        task_data = {
            "id": cutscene_data.get("id", ""),
            "title": cutscene_data.get("title", cutscene_data.get("id", "")),
            "description": cutscene_data.get("description", ""),
            "trigger": {"condition_type": "manual"},
            "steps": [],
            "completion_reward": cutscene_data.get("completion_reward", {}),
        }
        super().__init__(task_data)

        self.asset_manager = asset_manager
        self.type = cutscene_data.get("type", self.TYPE_IMAGE)
        self.video_path = cutscene_data.get("video")
        self.configured_duration = float(cutscene_data.get("duration", 0) or 0)
        self.dialogues = sorted(cutscene_data.get("dialogues", []), key=lambda item: item.get("time", 0))
        self.audio = cutscene_data.get("audio")
        self.sfx_click = cutscene_data.get("sfx_click")
        self.frames: List[CutsceneFrame] = [
            CutsceneFrame(
                image=frame.get("image", ""),
                duration=float(frame.get("duration", 2.0) or 2.0),
                dialogue=frame.get("dialogue"),
            )
            for frame in cutscene_data.get("frames", [])
        ]

        self.total_duration = self._resolve_duration()

    def _resolve_duration(self) -> float:
        if self.configured_duration > 0:
            return self.configured_duration

        if self.type == self.TYPE_IMAGE:
            return sum(frame.duration for frame in self.frames)

        if self.video_path:
            video_path = self.asset_manager.get_asset_path(self.video_path)
            if video_path.exists():
                cap = cv2.VideoCapture(str(video_path))
                try:
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    if fps > 0 and frame_count > 0:
                        return frame_count / fps
                finally:
                    cap.release()

        return 0.0

    def get_image_frame(self, time_seconds: float) -> Optional[CutsceneFrame]:
        if not self.frames:
            return None

        elapsed = 0.0
        for frame in self.frames:
            if elapsed <= time_seconds < elapsed + frame.duration:
                return frame
            elapsed += frame.duration
        return self.frames[-1]

    def get_current_dialogue(self, time_seconds: float) -> Optional[Dict]:
        if self.type == self.TYPE_IMAGE:
            frame = self.get_image_frame(time_seconds)
            return frame.dialogue if frame else None

        current_dialogue = None
        for dialogue in self.dialogues:
            if dialogue.get("time", 0.0) <= time_seconds:
                current_dialogue = dialogue
            else:
                break
        return current_dialogue


class CutscenePlayer:
    """播片播放器。"""

    def __init__(self, asset_manager):
        self.asset_manager = asset_manager
        self.cutscenes_data = asset_manager.load_cutscenes()
        self.cutscenes: Dict[str, CutsceneTask] = {}
        self.frame_cache: Dict[str, pygame.Surface] = {}

        self.current_cutscene: Optional[CutsceneTask] = None
        self.current_time = 0.0
        self.playback_state = PlaybackState.IDLE
        self.last_error: Optional[str] = None
        self.current_frame_surface: Optional[pygame.Surface] = None
        self.transition_alpha = 255

        self.progress_bar_rect: Optional[pygame.Rect] = None
        self.play_button_rect: Optional[pygame.Rect] = None
        self.is_dragging = False

        self.video_capture = None
        self.video_fps = 30.0
        self.video_frame_count = 0
        self.last_video_frame_index = -1

        self.video_frame_reader: Optional[VideoFrameReader] = None
        self.use_threaded_reader = True
        self.is_buffering = False
        buffer_config = self.cutscenes_data.get("cutscene_globals", {}).get("video_buffer_config", {})
        self.buffer_min_frames = int(buffer_config.get("buffer_min_frames", 8) or 8)
        self.buffer_max_wait = float(buffer_config.get("buffer_max_wait", 0.3) or 0.3)
        self.buffer_wait_time = 0.0
        self.current_audio_path: Optional[Path] = None
        self.audio_paused = False

        self._load_cutscenes()

    def _load_cutscenes(self):
        for cutscene_data in self.cutscenes_data.get("cutscenes", []):
            cutscene = CutsceneTask(cutscene_data, self.asset_manager)
            if cutscene.id:
                self.cutscenes[cutscene.id] = cutscene
        print(f"[播片系统] 加载了 {len(self.cutscenes)} 个播片任务")

    def start_cutscene(self, cutscene_id: str) -> bool:
        """开始播放指定播片。"""
        self._close_media()
        self.current_cutscene = self.cutscenes.get(cutscene_id)
        if not self.current_cutscene:
            self._start_error_cutscene(cutscene_id, f"播片不存在: {cutscene_id}")
            return True

        self.current_cutscene.status = Task.STATUS["available"]
        self.current_cutscene.start()
        self.current_time = 0.0
        self.playback_state = PlaybackState.PLAYING
        self.transition_alpha = 0
        self.is_dragging = False
        self.last_error = None
        self.current_frame_surface = None
        self.last_video_frame_index = -1
        self.is_buffering = False
        self.buffer_wait_time = 0.0

        if self.current_cutscene.type == CutsceneTask.TYPE_IMAGE:
            self.preload_cutscene_images(cutscene_id)
            if self.current_cutscene.audio:
                audio_path = self.asset_manager.get_asset_path(self.current_cutscene.audio)
                audio_duration = self._get_audio_duration(audio_path)
                if self.current_cutscene.total_duration <= 0 and audio_duration > 0:
                    self.current_cutscene.total_duration = audio_duration
                self._play_audio_path(audio_path)
            if self.current_cutscene.total_duration <= 0:
                self.current_cutscene.total_duration = 0.1
        elif not self._open_current_video():
            if self.current_cutscene.total_duration <= 0:
                self.current_cutscene.total_duration = 3.0
            self.current_frame_surface = self._create_error_surface(self.last_error or "视频加载失败")
        elif self.video_frame_reader is not None:
            self._start_buffering()

        print(f"[播片系统] 开始播放: {self.current_cutscene.title}")
        return True

    def _start_error_cutscene(self, cutscene_id: str, message: str):
        self.current_cutscene = CutsceneTask(
            {
                "id": cutscene_id,
                "title": "播片错误",
                "type": CutsceneTask.TYPE_VIDEO,
                "duration": 3.0,
            },
            self.asset_manager,
        )
        self.current_cutscene.status = Task.STATUS["available"]
        self.current_cutscene.start()
        self.current_time = 0.0
        self.playback_state = PlaybackState.PLAYING
        self.transition_alpha = 0
        self.is_dragging = False
        self.last_error = message
        self.current_frame_surface = self._create_error_surface(message)
        print(f"[播片系统] {message}")

    def _open_current_video(self) -> bool:
        if not self.current_cutscene or not self.current_cutscene.video_path:
            self.last_error = "当前播片没有配置视频文件"
            return False

        video_path = self.asset_manager.get_asset_path(self.current_cutscene.video_path)
        if not video_path.exists():
            self.last_error = f"视频文件不存在: {self.current_cutscene.video_path}"
            return False

        if self.use_threaded_reader and self._open_threaded_reader(video_path):
            self._play_audio_for(video_path)
            return True

        return self._open_cv_capture(video_path)

    def _open_threaded_reader(self, video_path: Path) -> bool:
        try:
            buffer_config = self.cutscenes_data.get("cutscene_globals", {}).get("video_buffer_config", {})
            buffer_size = int(buffer_config.get("buffer_size", 30) or 30)
            reader = VideoFrameReader(str(video_path), target_size=(SCREEN_WIDTH, SCREEN_HEIGHT), buffer_size=buffer_size)
            if not reader.is_valid:
                reader.release()
                return False

            self.video_frame_reader = reader
            self.video_fps = reader.get_frame_rate()
            self.video_frame_count = int(reader.get_duration() * self.video_fps)
            if self.current_cutscene:
                self.current_cutscene.total_duration = reader.get_duration()
            reader.start_preloading()
            print("[播片系统] 使用线程预读取器")
            return True
        except Exception as exc:
            print(f"[播片系统] 线程预读取失败，回退到同步读取: {exc}")
            self.video_frame_reader = None
            self.use_threaded_reader = False
            return False

    def _open_cv_capture(self, video_path: Path) -> bool:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            cap.release()
            self.last_error = f"无法打开视频: {self.current_cutscene.video_path if self.current_cutscene else video_path}"
            return False

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0 or frame_count <= 0:
            cap.release()
            self.last_error = f"视频元数据无效: {self.current_cutscene.video_path if self.current_cutscene else video_path}"
            return False

        self.video_capture = cap
        self.video_fps = fps
        self.video_frame_count = frame_count
        if self.current_cutscene:
            self.current_cutscene.total_duration = frame_count / fps
        self._play_audio_for(video_path)
        return True

    def _play_audio_for(self, video_path: Path):
        if not pygame.mixer.get_init() or not self.current_cutscene:
            return

        audio_path = self._resolve_audio_path(video_path)
        if not audio_path or not audio_path.exists():
            return

        self._play_audio_path(audio_path)

    def _play_audio_path(self, audio_path: Path):
        if not pygame.mixer.get_init() or not self.current_cutscene:
            return
        if not audio_path.exists():
            return

        try:
            from .config_manager import config_manager

            self.current_audio_path = audio_path
            pygame.mixer.music.set_volume(config_manager.get_music_volume() / 100.0)
            pygame.mixer.music.load(str(audio_path))
            pygame.mixer.music.play()
            self.audio_paused = False
            print(f"[播片系统] 播放音频: {audio_path.name}")
        except Exception as exc:
            print(f"[播片系统] 音频加载失败: {audio_path.name}: {exc}")

    def _get_audio_duration(self, audio_path: Path) -> float:
        if not pygame.mixer.get_init() or not audio_path.exists():
            return 0.0
        try:
            return float(pygame.mixer.Sound(str(audio_path)).get_length())
        except Exception:
            return 0.0

    def _resolve_audio_path(self, video_path: Path) -> Optional[Path]:
        if self.current_cutscene and self.current_cutscene.audio:
            return self.asset_manager.get_asset_path(self.current_cutscene.audio)
        candidate = video_path.with_suffix(".mp3")
        return candidate if candidate.exists() else None

    def _close_media(self):
        if self.video_frame_reader is not None:
            self.video_frame_reader.release()
            self.video_frame_reader = None

        if self.video_capture is not None:
            self.video_capture.release()
            self.video_capture = None

        self.last_video_frame_index = -1
        self._stop_audio()
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.unload()
            except AttributeError:
                pass
        self.current_audio_path = None

    def preload_cutscene_images(self, cutscene_id: str):
        cutscene = self.cutscenes.get(cutscene_id)
        if not cutscene or cutscene.type != CutsceneTask.TYPE_IMAGE:
            return

        for frame in cutscene.frames:
            if frame.image and frame.image not in self.frame_cache:
                self.frame_cache[frame.image] = self.asset_manager.load_image(
                    frame.image,
                    fallback_size=(SCREEN_WIDTH, SCREEN_HEIGHT),
                )

    preload_images = preload_cutscene_images

    def pause(self):
        if self.playback_state == PlaybackState.PLAYING:
            self.playback_state = PlaybackState.PAUSED
            self._pause_audio()

    def resume(self):
        if self.playback_state == PlaybackState.PAUSED:
            self.playback_state = PlaybackState.PLAYING
            self._resume_audio()

    def toggle_play_pause(self):
        if self.playback_state == PlaybackState.PLAYING:
            self.pause()
        elif self.playback_state == PlaybackState.PAUSED:
            self.resume()

    def seek_to(self, time_seconds: float):
        if not self.current_cutscene:
            return

        duration = max(0.0, self.current_cutscene.total_duration)
        self.current_time = max(0.0, min(time_seconds, duration))
        self.last_video_frame_index = -1

        if self.video_frame_reader is not None:
            self.video_frame_reader.seek_to(self.current_time)
            self._start_buffering()

        self._sync_audio_to_time(self.current_time)

    def seek_to_progress(self, progress: float):
        if self.current_cutscene:
            self.seek_to(progress * self.current_cutscene.total_duration)

    def _sync_audio_to_time(self, time_seconds: float):
        if not pygame.mixer.get_init() or not self.current_audio_path:
            return
        if not self.current_audio_path.exists():
            return

        try:
            from .config_manager import config_manager

            pygame.mixer.music.set_volume(config_manager.get_music_volume() / 100.0)
            pygame.mixer.music.load(str(self.current_audio_path))
            pygame.mixer.music.play(start=max(0.0, time_seconds))
            self.audio_paused = False
            if self.playback_state == PlaybackState.PAUSED:
                self._pause_audio()
        except Exception:
            pass

    def _pause_audio(self):
        if pygame.mixer.get_init() and self.current_audio_path and not self.audio_paused:
            pygame.mixer.music.pause()
            self.audio_paused = True

    def _resume_audio(self):
        if pygame.mixer.get_init() and self.current_audio_path and self.audio_paused:
            pygame.mixer.music.unpause()
            self.audio_paused = False

    def _stop_audio(self):
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
        self.audio_paused = False

    def _enforce_audio_state(self):
        if self.playback_state == PlaybackState.PAUSED:
            self._pause_audio()
        elif self.playback_state == PlaybackState.PLAYING:
            self._resume_audio()
        elif self.playback_state in {PlaybackState.FINISHED, PlaybackState.IDLE}:
            self._stop_audio()

    def finish(self):
        if not self.current_cutscene:
            return

        self.current_time = self.current_cutscene.total_duration
        self.playback_state = PlaybackState.FINISHED
        self._stop_audio()
        if self.current_cutscene.status == Task.STATUS["in_progress"]:
            self.current_cutscene.complete()

    def update(self, dt: float):
        if self.is_buffering and self.current_cutscene:
            self.buffer_wait_time += dt
            if self._is_buffer_ready():
                self.is_buffering = False
                self.buffer_wait_time = 0.0

        if self.is_buffering:
            self.transition_alpha = min(255, self.transition_alpha + dt * 500)
            self._enforce_audio_state()
            return

        if self.playback_state == PlaybackState.PLAYING and self.current_cutscene:
            self.current_time += dt
            if self.current_time >= self.current_cutscene.total_duration:
                self.finish()

        if self.transition_alpha < 255:
            self.transition_alpha = min(255, self.transition_alpha + dt * 500)

        self._enforce_audio_state()

    def is_finished(self) -> bool:
        return self.playback_state == PlaybackState.FINISHED

    def get_current_frame(self) -> Optional[pygame.Surface]:
        if not self.current_cutscene:
            return None

        if self.last_error:
            return self.current_frame_surface

        if self.current_cutscene.type == CutsceneTask.TYPE_VIDEO:
            return self._get_video_frame()

        frame = self.current_cutscene.get_image_frame(self.current_time)
        if not frame or not frame.image:
            return None
        return self.frame_cache.get(frame.image)

    def _get_video_frame(self) -> Optional[pygame.Surface]:
        if not self.current_cutscene:
            return self.current_frame_surface

        if self.video_frame_reader is not None and self.video_frame_reader.is_valid:
            if self.is_buffering and not self.video_frame_reader.has_frame(self.current_time):
                return self.current_frame_surface
            frame = self.video_frame_reader.get_frame(self.current_time)
            if frame:
                self.current_frame_surface = frame
            return self.current_frame_surface

        if not self.video_capture:
            return self.current_frame_surface

        target_index = int(self.current_time * self.video_fps)
        target_index = max(0, min(target_index, max(0, self.video_frame_count - 1)))

        if target_index == self.last_video_frame_index and self.current_frame_surface:
            return self.current_frame_surface

        if target_index != self.last_video_frame_index + 1:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, target_index)

        ok, frame = self.video_capture.read()
        if not ok:
            return self.current_frame_surface

        self.last_video_frame_index = target_index

        # Bolt: Optimize fallback player - resize on ndarray first, convert color, contiguous array, zero-copy surface
        resized = cv2.resize(frame, (SCREEN_WIDTH, SCREEN_HEIGHT), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        rgb_contig = np.ascontiguousarray(rgb)
        self.current_frame_surface = pygame.image.frombuffer(rgb_contig.data, (rgb_contig.shape[1], rgb_contig.shape[0]), 'RGB')

        return self.current_frame_surface

    def get_current_dialogue(self) -> Optional[Dict]:
        if not self.current_cutscene:
            return None
        return self.current_cutscene.get_current_dialogue(self.current_time)

    def get_current_frame_index(self) -> int:
        if not self.current_cutscene or self.current_cutscene.type != CutsceneTask.TYPE_IMAGE:
            return 0

        elapsed = 0.0
        for index, frame in enumerate(self.current_cutscene.frames):
            if elapsed <= self.current_time < elapsed + frame.duration:
                return index
            elapsed += frame.duration
        return max(0, len(self.current_cutscene.frames) - 1)

    def get_progress(self) -> float:
        if self.current_cutscene and self.current_cutscene.total_duration > 0:
            return self.current_time / self.current_cutscene.total_duration
        return 0.0

    def get_current_time_text(self) -> str:
        return self._format_time(self.current_time)

    def get_total_time_text(self) -> str:
        if not self.current_cutscene or self.current_cutscene.total_duration <= 0:
            return "--:--"
        return self._format_time(self.current_cutscene.total_duration)

    def _format_time(self, value: float) -> str:
        minutes = int(value // 60)
        seconds = int(value % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def handle_event(self, event: pygame.event.Event, mouse_pos: Tuple[int, int]) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            if self._is_play_button_clicked(mouse_pos):
                self.toggle_play_pause()
                return True
            if self._is_progress_bar_clicked(mouse_pos):
                self.is_dragging = True
                self.seek_to_progress(self._get_progress_from_position(mouse_pos[0]))
                return True

        elif event.type == pygame.MOUSEBUTTONUP and self.is_dragging:
            self.is_dragging = False
            return True

        elif event.type == pygame.MOUSEMOTION and self.is_dragging:
            self.seek_to_progress(self._get_progress_from_position(mouse_pos[0]))
            return True

        return False

    def _is_play_button_clicked(self, pos: Tuple[int, int]) -> bool:
        return bool(self.play_button_rect and self.play_button_rect.collidepoint(pos))

    def _is_progress_bar_clicked(self, pos: Tuple[int, int]) -> bool:
        return bool(self.progress_bar_rect and self.progress_bar_rect.collidepoint(pos))

    def _get_progress_from_position(self, x: float) -> float:
        if not self.progress_bar_rect:
            return 0.0
        return max(0.0, min(1.0, (x - self.progress_bar_rect.left) / self.progress_bar_rect.width))

    def reset(self):
        self._close_media()
        self.current_cutscene = None
        self.current_time = 0.0
        self.playback_state = PlaybackState.IDLE
        self.transition_alpha = 0
        self.is_dragging = False
        self.current_frame_surface = None
        self.last_error = None
        self.is_buffering = False
        self.buffer_wait_time = 0.0

    def get_available_cutscenes(self) -> List[str]:
        return list(self.cutscenes.keys())

    def _start_buffering(self):
        if self.video_frame_reader and self.video_frame_reader.is_valid:
            self.is_buffering = True
            self.buffer_wait_time = 0.0

    def _is_buffer_ready(self) -> bool:
        if not self.video_frame_reader or not self.video_frame_reader.is_valid:
            return True
        buffered = self.video_frame_reader.get_buffered_ahead(self.current_time)
        return buffered >= self.buffer_min_frames or self.buffer_wait_time >= self.buffer_max_wait

    def _create_error_surface(self, message: str) -> pygame.Surface:
        surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        surface.fill(COLOR_BG_DARK)

        title_font = self.asset_manager.load_font(42)
        body_font = self.asset_manager.load_font(26)

        title = title_font.render("播片无法播放", True, COLOR_CHAMPAGNE)
        surface.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 45)))

        lines = self._wrap_text(message, body_font, 980)
        start_y = SCREEN_HEIGHT // 2 + 20
        for index, line in enumerate(lines):
            text = body_font.render(line, True, COLOR_TEXT)
            surface.blit(text, text.get_rect(center=(SCREEN_WIDTH // 2, start_y + index * 36)))

        hint = body_font.render("将自动返回，或按 ESC 跳过", True, (140, 145, 155))
        surface.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 120)))
        return surface

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        lines: List[str] = []
        current = ""
        for char in text:
            candidate = current + char
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = char
        if current:
            lines.append(current)
        return lines or [text]


Cutscene = CutsceneTask
