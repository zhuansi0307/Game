## 2026-08-13 - Pygame Video Rendering Zero-Copy Optimization
**Learning:** Converting OpenCV BGR frames to Pygame Surfaces via `np.transpose` and `pygame.surfarray.make_surface` is a significant performance bottleneck due to excessive memory copying and matrix manipulation.
**Action:** Use `cv2.resize` on BGR frames before converting to RGB to reduce processing overhead. Then, ensure the array is contiguous and map it directly to a Pygame Surface using `pygame.image.frombuffer(frame.data, (frame.shape[1], frame.shape[0]), 'RGB')` for a zero-copy operation.
