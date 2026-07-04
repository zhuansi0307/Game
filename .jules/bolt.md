## 2024-05-24 - Pygame Video Rendering Optimization
**Learning:** In this Pygame/OpenCV integration, rendering video frames via `np.transpose` and `pygame.surfarray.make_surface` is an expensive bottleneck.
**Action:** Use `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` directly on contiguous `ndarray`s to map OpenCV frames to Pygame Surfaces in a zero-copy manner. Ensure you pass the size tuple as `(width, height)`. Use `cv2.resize` instead of `pygame.transform.smoothscale` before mapping.
