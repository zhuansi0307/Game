## 2024-07-18 - Pygame Frame Conversion Optimization
**Learning:** The default method of creating a pygame surface using `pygame.surfarray.make_surface` after a numpy array transpose is very slow (~1.8s for 100 frames). Moreover, resizing the frame using `pygame.transform.smoothscale` is also slow.
**Action:** Use `cv2.resize` instead of `pygame.transform.smoothscale` for resizing, and use `pygame.image.frombuffer(rgb.data, (width, height), 'RGB')` with an `np.ascontiguousarray` block instead of `make_surface` and transposing. This is about 4x faster (~0.45s for 100 frames).
