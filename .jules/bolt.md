
## 2025-02-27 - [Optimize video frame Pygame surface creation]
**Learning:** Using `np.transpose` and `pygame.surfarray.make_surface` is slow due to memory copies. Pygame 2.x supports zero-copy via `pygame.image.frombuffer` but it needs contiguous memory (`np.ascontiguousarray`) and the correct size tuple `(width, height)`.
**Action:** Always prefer `pygame.image.frombuffer` and `cv2.resize` for video rendering in Pygame instead of `surfarray` and `pygame.transform.smoothscale`.
