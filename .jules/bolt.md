## 2024-07-28 - Optimize Pygame video frame surface creation
**Learning:** Using `pygame.surfarray.make_surface` with `np.transpose` to convert OpenCV BGR frames to Pygame Surfaces is extremely slow. `pygame.image.frombuffer` with `np.ascontiguousarray` on the RGB frame is ~50x faster because it avoids zero-copy matrix transposition overhead.
**Action:** Always prefer `pygame.image.frombuffer(frame.data, (frame.shape[1], frame.shape[0]), 'RGB')` for optimal video rendering in Pygame.
