## 2024-10-28 - [Fast Pygame Video Rendering]
**Learning:** In Pygame + OpenCV video playback, using `pygame.surfarray.make_surface` combined with `np.transpose` is a major performance bottleneck, and `pygame.transform.smoothscale` is slower than OpenCV native resizing.
**Action:** Always resize frames with OpenCV *before* color space conversion (BGR to RGB), and use `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')` instead of surfarray for ~10-15x faster frame-to-surface creation.
