## 2025-02-18 - Pygame Per-Frame Scaling Bottleneck
**Learning:** Calling `pygame.transform.smoothscale()` on every single frame in the render loop is a significant performance bottleneck in Pygame applications, particularly for large sizes like 1080p.
**Action:** Always check if `surface.get_size() == target_size` before applying scaling transformations inside a render loop to avoid redundant computation.
