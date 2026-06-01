## 2024-06-01 - Pygame Video Rendering Bottleneck
**Learning:** `pygame.surfarray.make_surface` combined with `np.transpose` is extremely slow (often ~1-2 seconds for 100 frames). Native `pygame.image.frombuffer` on a contiguous array is practically instantaneous (~0.0008 seconds for 100 frames), achieving a zero-copy mapping.
**Action:** When mapping OpenCV frames to Pygame Surfaces, ALWAYS use `np.ascontiguousarray` followed by `pygame.image.frombuffer(frame.data, size, 'RGB')`. Additionally, use `cv2.resize` instead of `pygame.transform.smoothscale`.
