## 2024-06-08 - [Pygame Video Frame Rendering Optimization]
**Learning:** `pygame.surfarray.make_surface` and `np.transpose` are very slow for rendering video frames, especially when combined with `pygame.transform.smoothscale`. We can map OpenCV frames directly to Pygame Surfaces using `pygame.image.frombuffer` which avoids expensive memory copies.
**Action:** Use `cv2.resize` to handle frame scaling and `pygame.image.frombuffer` to create the surface directly from the contiguous ndarray.
