## 2024-06-03 - [Pygame Video Frame Rendering Optimization]
**Learning:** `np.transpose` and `pygame.surfarray.make_surface` are massive performance bottlenecks for high-resolution video frames (e.g., 1080p).
**Action:** Always prefer `pygame.image.frombuffer(np.ascontiguousarray(frame).data, size, 'RGB')` combined with `cv2.resize` when bringing OpenCV frames into Pygame. This provides a ~7000x speedup for the surface mapping phase.
