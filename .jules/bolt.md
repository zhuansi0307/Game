## 2024-05-19 - Pygame/OpenCV frame rendering optimization
**Learning:** In Pygame, `pygame.surfarray.make_surface(np.transpose(...))` is very slow (e.g. ~11-26ms per frame).
**Action:** Use `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` combined with `np.ascontiguousarray` for zero-copy mapping of OpenCV frames to Pygame Surfaces, significantly speeding it up (~0.2-1.5ms per frame). Also, perform `cv2.resize` instead of `pygame.transform.smoothscale` for better performance.
