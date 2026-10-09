
## 2024-05-18 - Pygame Video Rendering Optimization
**Learning:** In Pygame, rendering video frames natively via `pygame.surfarray.make_surface` and `np.transpose` is highly inefficient and creates significant overhead for real-time video playback. Alternatively, converting `ndarray` straight to bytes using `.tobytes()` and loading it via `pygame.image.frombuffer` offers a 10-15x performance increase.
Furthermore, applying OpenCV operations like `cv2.resize` BEFORE `cv2.cvtColor` color conversion reduces the overall pixel processing overhead.
**Action:** When working with Pygame video rendering pipelines, ALWAYS resize before color conversion, and use `pygame.image.frombuffer(buffer, size, format)` instead of `np.transpose` combined with `pygame.surfarray.make_surface`.
