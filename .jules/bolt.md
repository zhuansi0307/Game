
## 2023-11-02 - [Video Frame Pygame Surface Conversion Optimization]
**Learning:** `pygame.surfarray.make_surface` + `np.transpose` is 10-20x slower than `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')` when converting video frames to pygame surfaces.
**Action:** Always use `pygame.image.frombuffer` for creating pygame surfaces from raw video frames instead of `pygame.surfarray.make_surface` + `np.transpose`.
