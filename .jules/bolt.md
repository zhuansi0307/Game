
## 2024-05-18 - [Pygame Video Frame Rendering Optimization]
**Learning:** Pygame + OpenCV video frame rendering optimization: using `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')` is extremely fast (much faster than `pygame.surfarray.make_surface` + `np.transpose`). Also, using `cv2.resize` directly on the `ndarray` *before* color conversion (`cv2.cvtColor`) and surface creation minimizes pixel processing and is measurably faster.
**Action:** Always resize frames natively with OpenCV before converting color spaces or Pygame surfaces to minimize overhead.
