## 2024-05-24 - [Pygame Video Frame Optimization]
**Learning:** `pygame.surfarray.make_surface` + `np.transpose` is highly inefficient and creates expensive memory copies. Pygame 2.x doesn't natively support BGR buffers so frames must be converted to RGB. OpenCV `cv2.resize` is significantly faster than `pygame.transform.smoothscale`.
**Action:** Always prefer using `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` combined with `np.ascontiguousarray` for zero-copy surface creation when rendering OpenCV frames in Pygame.
