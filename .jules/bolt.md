## 2023-11-20 - Pygame Video Rendering Optimization
**Learning:** In Pygame, `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')` combined with native OpenCV resizing (`cv2.resize`) before color conversion is significantly faster (~20x) than using `pygame.surfarray.make_surface` on a transposed array followed by `pygame.transform.smoothscale`.
**Action:** Always resize frames using OpenCV *before* any color conversions or Pygame surface creations. Use `pygame.image.frombuffer` instead of `surfarray.make_surface` + transpose for creating Pygame surfaces from video frames.
