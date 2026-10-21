## 2026-10-21 - Optimize Pygame Video Frame Rendering
**Learning:** Pygame's `surfarray.make_surface` combined with `np.transpose` is significantly slower (up to 10x) than using `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')` for converting OpenCV frames to Pygame surfaces. Additionally, resizing an image before color conversion (`cv2.cvtColor`) requires less computation.
**Action:** Always prefer `pygame.image.frombuffer` for rendering raw video frames to Pygame surfaces and perform OpenCV `resize` operations before `cvtColor`.
