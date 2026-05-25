## 2024-05-01 - Optimize Pygame OpenCV Video Surface Creation
**Learning:** `np.transpose` combined with `pygame.surfarray.make_surface` is a significant performance bottleneck when rendering OpenCV video frames in Pygame, causing unnecessary memory copies.
**Action:** Always use `cv2.resize` (if needed) to scale the ndarray, ensure it is contiguous with `np.ascontiguousarray`, and use `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` for zero-copy, high-performance frame mapping (~10x faster).
