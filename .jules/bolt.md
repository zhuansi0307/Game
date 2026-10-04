## 2025-03-02 - [Video Frame Rendering Optimization]
**Learning:** For Pygame + OpenCV video frame rendering, using `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')` is extremely fast (5-10x faster than the `pygame.surfarray.make_surface` + `np.transpose` approach). Also, using `cv2.resize` directly on the `ndarray` *before* color conversion (`cv2.cvtColor`) and surface creation minimizes pixel processing and is measurably faster.
**Action:** Always resize frames natively with OpenCV before converting color spaces or Pygame surfaces to minimize overhead.
