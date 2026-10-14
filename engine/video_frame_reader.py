"""
视频帧预读取模块
后台线程负责 OpenCV 解码和缩放，主线程负责创建 pygame Surface。
"""

import threading
import time
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
import pygame


class VideoFrameReader:
    """线程安全的视频帧预读取器。"""

    def __init__(self, video_path: str, target_size: Tuple[int, int] = (1920, 1080), buffer_size: int = 24):
        """
        初始化视频帧读取器。
        :param video_path: 视频文件路径
        :param target_size: 输出尺寸 (width, height)
        :param buffer_size: 目标预读缓存帧数
        """
        self.video_path = video_path
        self.target_size = target_size
        self.buffer_size = max(4, buffer_size)
        self.max_cache_size = self.buffer_size * 3

        self.fps = 0.0
        self.frame_count = 0
        self.total_duration = 0.0
        self.is_valid = False

        self._preload_cap = None
        self._sync_cap = None
        self._sync_lock = threading.Lock()

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._frame_cache: Dict[int, np.ndarray] = {}
        self._surface_cache: Dict[int, pygame.Surface] = {}
        self._playhead_index = 0
        self._read_index = 0
        self._seek_request: Optional[int] = None

        self.frames_read = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.direct_reads = 0

        self._initialize()

    def _initialize(self):
        """打开视频并读取元数据。"""
        probe = cv2.VideoCapture(str(self.video_path))
        if not probe.isOpened():
            print(f"[视频预读取] 无法打开视频: {self.video_path}")
            return

        self.fps = probe.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(probe.get(cv2.CAP_PROP_FRAME_COUNT))
        probe.release()

        if self.fps <= 0 or self.frame_count <= 0:
            print(f"[视频预读取] 视频元数据无效: {self.video_path}")
            return

        self.total_duration = self.frame_count / self.fps
        self._preload_cap = cv2.VideoCapture(str(self.video_path))
        self._sync_cap = cv2.VideoCapture(str(self.video_path))

        if not self._preload_cap.isOpened() or not self._sync_cap.isOpened():
            self.release()
            print(f"[视频预读取] 无法创建读取句柄: {self.video_path}")
            return

        self.is_valid = True
        print(f"[视频预读取] 加载视频: {self.video_path}")
        print(f"  - 帧率: {self.fps:.1f} FPS")
        print(f"  - 总帧数: {self.frame_count}")
        print(f"  - 时长: {self.total_duration:.1f}秒")
        print(f"  - 预读缓存: {self.buffer_size}帧")

    def start_preloading(self):
        """启动后台预读取线程。"""
        if not self.is_valid or self._thread:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._preload_worker, name="VideoFrameReader", daemon=True)
        self._thread.start()
        print("[视频预读取] 启动预读取线程")

    def _preload_worker(self):
        """后台线程：围绕当前播放头预读一段帧窗口。"""
        while not self._stop_event.is_set() and self.is_valid:
            seek_index = None
            with self._lock:
                if self._seek_request is not None:
                    seek_index = self._seek_request
                    self._seek_request = None
                    self._read_index = seek_index
                    self._frame_cache.clear()
                    self._surface_cache.clear()

                playhead = self._playhead_index
                ahead = self._count_ahead_locked(playhead)
                behind = self._count_behind_locked(playhead)
                total_cached = len(self._frame_cache)

                if ahead >= self.buffer_size or total_cached >= self.buffer_size:
                    needs_wait = True
                else:
                    needs_wait = False
                    read_index = max(self._read_index, playhead)

            if seek_index is not None:
                self._preload_cap.set(cv2.CAP_PROP_POS_FRAMES, seek_index)

            if needs_wait:
                time.sleep(0.002)
                continue

            if read_index >= self.frame_count:
                time.sleep(0.005)
                continue

            current_pos = int(self._preload_cap.get(cv2.CAP_PROP_POS_FRAMES))
            if current_pos != read_index:
                self._preload_cap.set(cv2.CAP_PROP_POS_FRAMES, read_index)

            ret, frame = self._preload_cap.read()
            if not ret:
                time.sleep(0.005)
                continue

            processed = self._process_frame(frame)
            with self._lock:
                self._frame_cache[read_index] = processed
                self._read_index = read_index + 1
                self.frames_read += 1
                self._trim_cache_locked()

    def _count_ahead_locked(self, playhead: int) -> int:
        """统计播放头前方已经缓存的帧数。"""
        end = min(self.frame_count, playhead + self.buffer_size)
        return sum(1 for idx in self._frame_cache if playhead <= idx < end)

    def _count_behind_locked(self, playhead: int) -> int:
        """统计播放头后方已经缓存的帧数。"""
        start = max(0, playhead - self.buffer_size // 2)
        return sum(1 for idx in self._frame_cache if start <= idx < playhead)

    def _trim_cache_locked(self):
        """裁剪缓存，保留播放头附近更大的窗口。"""
        min_keep = max(0, self._playhead_index - self.buffer_size // 2)
        max_keep = min(self.frame_count, self._playhead_index + self.buffer_size)

        for idx in list(self._frame_cache.keys()):
            if idx < min_keep or idx >= max_keep:
                self._frame_cache.pop(idx, None)
                self._surface_cache.pop(idx, None)

        while len(self._frame_cache) > self.max_cache_size:
            farthest = max(self._frame_cache.keys(), key=lambda idx: abs(idx - self._playhead_index))
            self._frame_cache.pop(farthest, None)
            self._surface_cache.pop(farthest, None)

    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        """BGR 帧转 RGB 并缩放到目标尺寸。"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width = rgb_frame.shape[:2]
        target_width, target_height = self.target_size

        if (width, height) != self.target_size:
            interpolation = cv2.INTER_AREA if width > target_width or height > target_height else cv2.INTER_LINEAR
            rgb_frame = cv2.resize(rgb_frame, self.target_size, interpolation=interpolation)

        return np.ascontiguousarray(rgb_frame)

    def get_frame(self, time_seconds: float) -> Optional[pygame.Surface]:
        """获取指定时间的帧，命中缓存时不触发同步解码。"""
        if not self.is_valid:
            return None

        frame_index = self._time_to_frame_index(time_seconds)
        with self._lock:
            self._playhead_index = frame_index
            self._trim_cache_locked()

            cached_surface = self._surface_cache.get(frame_index)
            if cached_surface is not None:
                self.cache_hits += 1
                return cached_surface

            cached_frame = self._frame_cache.get(frame_index)
            if cached_frame is not None:
                self.cache_hits += 1

        if cached_frame is not None:
            surface = self._frame_to_surface(cached_frame)
            with self._lock:
                self._surface_cache[frame_index] = surface
            return surface

        self.cache_misses += 1
        frame = self._read_frame_sync(frame_index)
        if frame is None:
            return None

        surface = self._frame_to_surface(frame)
        with self._lock:
            self._frame_cache[frame_index] = frame
            self._surface_cache[frame_index] = surface
            if self._read_index < frame_index + 1:
                self._read_index = frame_index + 1
            self._trim_cache_locked()

        return surface

    def _read_frame_sync(self, frame_index: int) -> Optional[np.ndarray]:
        """缓存未命中时主线程兜底读取一帧，使用独立 capture 避免与后台线程争用。"""
        with self._sync_lock:
            if not self._sync_cap:
                return None
            self._sync_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame = self._sync_cap.read()

        if not ret:
            return None

        self.direct_reads += 1
        return self._process_frame(frame)

    def _frame_to_surface(self, frame: np.ndarray) -> pygame.Surface:
        """在主线程把 RGB ndarray 转成 pygame Surface。"""
        # Optimize: using frombuffer is extremely fast compared to make_surface + transpose
        height, width = frame.shape[:2]
        return pygame.image.frombuffer(frame.tobytes(), (width, height), 'RGB')

    def _time_to_frame_index(self, time_seconds: float) -> int:
        """秒数转帧索引。"""
        frame_index = int(time_seconds * self.fps)
        return max(0, min(frame_index, self.frame_count - 1))

    def seek_to(self, time_seconds: float):
        """跳转到指定时间，并通知后台线程重建预读窗口。"""
        if not self.is_valid:
            return

        frame_index = self._time_to_frame_index(time_seconds)
        with self._lock:
            self._playhead_index = frame_index
            self._read_index = frame_index
            self._seek_request = frame_index
            self._frame_cache.clear()
            self._surface_cache.clear()

    def get_frame_rate(self) -> float:
        """获取视频帧率。"""
        return self.fps

    def get_duration(self) -> float:
        """获取视频时长。"""
        return self.total_duration

    def get_cache_stats(self) -> dict:
        """获取缓存统计。"""
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total * 100) if total else 0.0
        with self._lock:
            cached_frames = len(self._frame_cache)

        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "cached_frames": cached_frames,
            "frames_read": self.frames_read,
            "direct_reads": self.direct_reads,
        }

    def get_buffered_ahead(self, time_seconds: float) -> int:
        """获取指定时间点之后连续缓存了多少帧。"""
        if not self.is_valid:
            return 0

        frame_index = self._time_to_frame_index(time_seconds)
        with self._lock:
            count = 0
            for idx in range(frame_index, min(self.frame_count, frame_index + self.buffer_size)):
                if idx not in self._frame_cache:
                    break
                count += 1
            return count

    def has_frame(self, time_seconds: float) -> bool:
        """检查指定时间点的帧是否已在缓存中。"""
        if not self.is_valid:
            return False

        frame_index = self._time_to_frame_index(time_seconds)
        with self._lock:
            return frame_index in self._frame_cache or frame_index in self._surface_cache

    def clear_cache(self):
        """清空缓存。"""
        with self._lock:
            self._frame_cache.clear()
            self._surface_cache.clear()

    def stop(self):
        """停止预读取线程。"""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def release(self):
        """释放资源。"""
        stats = self.get_cache_stats() if self.is_valid else None
        self.stop()

        if self._preload_cap:
            self._preload_cap.release()
            self._preload_cap = None
        if self._sync_cap:
            self._sync_cap.release()
            self._sync_cap = None

        self.clear_cache()
        self.is_valid = False

        if stats:
            print(f"[视频预读取] 释放资源: {self.video_path}")
            print(
                "[视频预读取] 缓存统计: "
                f"命中{stats['cache_hits']}次, 未命中{stats['cache_misses']}次, "
                f"命中率{stats['hit_rate']}, 后台读取{stats['frames_read']}帧, "
                f"同步读取{stats['direct_reads']}帧"
            )


class VideoPlayer:
    """独立测试用的视频播放器封装。"""

    def __init__(self, video_path: str, target_size: Tuple[int, int] = (1920, 1080)):
        self.frame_reader = VideoFrameReader(video_path, target_size)
        self.current_time = 0.0
        self.is_playing = False

    def play(self):
        """开始播放。"""
        if self.frame_reader.is_valid:
            self.frame_reader.start_preloading()
            self.is_playing = True

    def pause(self):
        """暂停播放。"""
        self.is_playing = False

    def seek(self, time_seconds: float):
        """跳转到指定时间。"""
        self.current_time = max(0.0, min(time_seconds, self.frame_reader.get_duration()))
        self.frame_reader.seek_to(self.current_time)

    def update(self, dt: float):
        """更新播放时间。"""
        if self.is_playing:
            self.current_time += dt
            if self.current_time >= self.frame_reader.get_duration():
                self.current_time = self.frame_reader.get_duration()
                self.is_playing = False

    def get_current_frame(self) -> Optional[pygame.Surface]:
        """获取当前帧。"""
        return self.frame_reader.get_frame(self.current_time)

    def release(self):
        """释放资源。"""
        self.frame_reader.release()

    def get_stats(self) -> dict:
        """获取性能统计。"""
        return self.frame_reader.get_cache_stats()
