## 2024-06-17 - Pygame Video Surface Creation
**Learning:** `pygame.surfarray.make_surface` combined with `np.transpose` is extremely slow (~1 second for 100 frames) due to heavy array copies. OpenCV `cv2.resize` is significantly faster than `pygame.transform.smoothscale`.
**Action:** Use `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` for zero-copy mapping of contiguous ndarrays to Pygame Surfaces. Always use `cv2.resize` on the ndarray before converting to a surface.
