
## 2026-10-25 - [Optimize Video Frame Rendering]
**Learning:** In Pygame + OpenCV video frame rendering, using `pygame.surfarray.make_surface` combined with `np.transpose` is very slow compared to `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')`. Additionally, performing `cv2.resize` natively on the BGR frame *before* `cv2.cvtColor` is significantly faster since it reduces the number of pixels that need color space conversion.
**Action:** Always resize frames natively with OpenCV *before* converting color spaces or Pygame surfaces, and use `pygame.image.frombuffer` to minimize overhead.
