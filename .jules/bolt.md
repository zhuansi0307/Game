
## 2024-05-18 - Pygame Surface Creation Optimization
**Learning:** In Pygame, creating surfaces from numpy arrays using `pygame.surfarray.make_surface` requires an array transpose and is slow (approx. 0.9s per 100 frames). Using `pygame.image.frombuffer(array.tobytes(), size, 'RGB')` is extremely fast (approx. 0.06s per 100 frames), resulting in ~15x speedup.
Additionally, for video frames needing resize, resizing the ndarray with OpenCV (`cv2.resize`) *before* color conversion (`cv2.cvtColor`) and *before* surface creation minimizes pixel processing and is measurably faster (1.8x speedup).
**Action:** Always use `pygame.image.frombuffer` for converting RGB `np.ndarray` to Pygame `Surface` in performance paths. Always resize frames natively with OpenCV before color conversion and surface creation.
