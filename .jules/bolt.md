## 2024-05-24 - Zero-Copy Frame Rendering
**Learning:** `np.transpose` followed by `pygame.surfarray.make_surface` is an O(N) operation that creates excessive memory copies per frame. Using `pygame.image.frombuffer` with contiguous memory mapped from OpenCV is essentially O(1) and >100x faster for high-res video. Also, resizing frames before color conversion saves significant computation.
**Action:** Always prefer `pygame.image.frombuffer` for Pygame/OpenCV integration, and defer color conversions until after spatial reductions (resizing) are applied.
