## 2024-05-14 - Pygame Surface Creation Optimization
**Learning:** Found an optimization specifically called out in memory for converting OpenCV frames to Pygame Surfaces. Using `pygame.image.frombuffer` avoids `np.transpose` and `pygame.surfarray.make_surface`.
**Action:** Apply this specific optimization in `_frame_to_surface` within `engine/video_frame_reader.py`.
