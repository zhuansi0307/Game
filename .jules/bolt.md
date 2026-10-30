
## 2025-02-23 - Optimize Pygame Surface Creation
**Learning:** For converting OpenCV frames (ndarrays) to Pygame Surfaces, `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')` is extremely fast (10-15x faster than the `pygame.surfarray.make_surface` + `np.transpose` approach). Also, using `cv2.resize` directly on the `ndarray` *before* color conversion (`cv2.cvtColor`) and surface creation minimizes pixel processing and is measurably faster. Always resize frames natively with OpenCV before converting color spaces or Pygame surfaces to minimize overhead.
**Action:** Always prefer `pygame.image.frombuffer` for real-time video rendering pipelines in Pygame, and ensure heavy pixel operations like color conversions are done *after* spatial downscaling.
