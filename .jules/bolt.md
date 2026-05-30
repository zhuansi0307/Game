## 2024-05-24 - Pygame Video Performance
**Learning:** Pygame `pygame.surfarray.make_surface` after `np.transpose` is very slow. Using `pygame.image.frombuffer` directly with contiguous RGB array is thousands of times faster.
**Action:** Replace `pygame.surfarray.make_surface` with `pygame.image.frombuffer` for mapping OpenCV frames to Pygame surfaces.
