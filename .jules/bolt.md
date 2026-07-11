
## 2024-05-18 - Pygame Zero-Copy Surface Creation & Efficient Resizing
**Learning:** `pygame.surfarray.make_surface` and `np.transpose` are very slow for rendering video frames due to allocating and copying memory. In addition, `pygame.transform.smoothscale` is significantly slower than OpenCV's `cv2.resize`.
**Action:** Use `pygame.image.frombuffer(frame_cont.data, (width, height), 'RGB')` with an `np.ascontiguousarray` (after converting BGR to RGB) for zero-copy mapping. When scaling is required, resize the ndarray first using `cv2.resize` instead of Pygame's smoothscale. Note: `frombuffer` takes size as `(width, height)`, unlike numpy's `(height, width)`.
