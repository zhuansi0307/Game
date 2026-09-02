## 2024-05-16 - [Video Frame Conversion Optimization]
**Learning:** Pygame `pygame.surfarray.make_surface` and `np.transpose` are significantly slower than `pygame.image.frombuffer(rgb.data, (rgb.shape[1], rgb.shape[0]), 'RGB')`. Additionally, `cv2.resize` on a numpy array is faster than `pygame.transform.smoothscale`.
**Action:** Always prefer `cv2.resize` and `pygame.image.frombuffer` for rendering frames from OpenCV video stream to Pygame surfaces.
