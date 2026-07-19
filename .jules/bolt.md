## 2024-07-19 - Pygame Surface Creation Optimization
**Learning:** Using `pygame.surfarray.make_surface` combined with `np.transpose` creates unnecessary copies and CPU overhead when converting OpenCV frames to Pygame surfaces.
**Action:** Use `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` with a contiguous array for zero-copy surface creation.
