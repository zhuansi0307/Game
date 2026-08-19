## 2024-05-15 - Pygame Surface Creation Optimization
**Learning:** Using `pygame.surfarray.make_surface` with `np.transpose` is significantly slower than `pygame.image.frombuffer` with a contiguous array for video frame rendering.
**Action:** Prefer `pygame.image.frombuffer` for high-performance surface creation from raw frame buffers.
