## 2025-02-27 - Pygame Surface Creation Optimization
**Learning:** In Pygame, `pygame.surfarray.make_surface` coupled with `np.transpose` is highly inefficient for large arrays (like video frames). `numpy` transpose creates a view, but `make_surface` forces a copy.
**Action:** Use `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` which is practically zero-copy and orders of magnitude faster (0.9s -> 0.0003s for 100 frames). Wait, ensure `np.ascontiguousarray()` was applied after any image manipulation like resizing, since frombuffer requires contiguous C-order buffer.
