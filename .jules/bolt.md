## 2024-05-23 - Pygame OpenCV Video Frame Rendering Optimization
**Learning:** `np.transpose` followed by `pygame.surfarray.make_surface` and `pygame.transform.smoothscale` is a massive performance bottleneck for mapping OpenCV frames to Pygame Surfaces. The `make_surface` requires deep copying and `transpose` is O(N).
**Action:** Use zero-copy `pygame.image.frombuffer(frame.data, (frame.shape[1], frame.shape[0]), 'RGB')` for surface conversion and use `cv2.resize` on the ndarray prior to converting for up to 10x speedup. Ensure the ndarray is contiguous using `np.ascontiguousarray`.
