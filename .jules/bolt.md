## 2025-02-23 - Pygame Video Rendering Optimization
**Learning:** Mapping OpenCV arrays to Pygame Surfaces via `pygame.surfarray.make_surface` alongside `np.transpose` is excessively slow. Furthermore, resizing RGB frames is less efficient than resizing the BGR frames before color conversion.
**Action:** Use `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` as a zero-copy mapping (ensuring frame contiguity with `np.ascontiguousarray`), and apply `cv2.resize` to the `ndarray` prior to executing `cv2.cvtColor`.
