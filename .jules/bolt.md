## 2024-05-30 - Pygame Video Rendering Optimization
**Learning:** `pygame.surfarray.make_surface` combined with `np.transpose` is slower than `pygame.image.frombytes` for creating surfaces from numpy arrays, particularly for high resolution video frames (1920x1080).
**Action:** Replace `np.transpose` and `pygame.surfarray.make_surface` with `pygame.image.frombytes(frame.tobytes(), (frame.shape[1], frame.shape[0]), 'RGB')` in `engine/video_frame_reader.py` to improve frame conversion speed.
