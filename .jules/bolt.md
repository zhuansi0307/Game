
## 2024-05-18 - Pygame Video Frame Rendering Optimization
**Learning:** In Pygame, mapping OpenCV frames to Pygame Surfaces using `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` is significantly faster (~17x) than using `np.transpose` followed by `pygame.surfarray.make_surface` and `pygame.transform.smoothscale`. Additionally, using `cv2.resize` directly on the ndarray (before color conversion for maximum efficiency) is much faster than Pygame's `smoothscale`.
**Action:** Always prefer `pygame.image.frombuffer` over `make_surface` for streaming video frames in Pygame, and ensure the array is contiguous and in RGB format. Use `cv2.resize` instead of Pygame's transform functions for frame resizing.
