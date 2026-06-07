## 2023-10-27 - [Pygame Surface Creation Bottleneck]
**Learning:** `pygame.surfarray.make_surface` coupled with `np.transpose` is extremely slow (often taking ~1 second for 100 frames) compared to a zero-copy mapping.
**Action:** Use `pygame.image.frombuffer(rgb.data, (SCREEN_WIDTH, SCREEN_HEIGHT), 'RGB')` combined with `np.ascontiguousarray` and `cv2.resize` to achieve near-instantaneous Surface creation (~0.0002 seconds for 100 frames without resize, and ~0.2 seconds with `cv2.resize`).
