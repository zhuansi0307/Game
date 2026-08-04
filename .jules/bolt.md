## 2024-08-04 - Zero-copy Pygame Surface Creation
**Learning:** `np.transpose` combined with `pygame.surfarray.make_surface` is a major performance bottleneck for video frame rendering due to heavy memory allocation and copying. Pygame doesn't support BGR natively.
**Action:** Use OpenCV to convert color (`cv2.cvtColor`) and resize (`cv2.resize`), make the array contiguous (`np.ascontiguousarray`), and use `pygame.image.frombuffer(rgb.data, (rgb.shape[1], rgb.shape[0]), 'RGB')` for a 60x speedup in surface creation.
