## 2023-10-24 - [OpenCV + Pygame Video Frame Optimization]
**Learning:** Pygame's `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')` is extremely fast (10-15x faster than `pygame.surfarray.make_surface` + `np.transpose`). Also, using `cv2.resize` directly on the `ndarray` *before* color conversion (`cv2.cvtColor`) and surface creation minimizes pixel processing and is measurably faster (roughly 2x faster).
**Action:** When rendering OpenCV frames in Pygame, always resize the raw BGR frame first, convert to RGB, and then use `pygame.image.frombuffer`.
