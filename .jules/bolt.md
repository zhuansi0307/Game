
## 2024-05-18 - [Pygame Surface Creation Optimization]
**Learning:** `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` is extremely fast for mapping OpenCV frames (ndarrays) to Pygame Surfaces. It allows a zero-copy approach. In contrast, `pygame.surfarray.make_surface` and `np.transpose` are significantly slower. Also `cv2.resize` on the array level is faster than `pygame.transform.smoothscale`. The array must be contiguous (`np.ascontiguousarray`) and converted to RGB first.
**Action:** When working with OpenCV and Pygame to render videos or frames, always prefer `pygame.image.frombuffer` on a contiguous RGB array over `pygame.surfarray.make_surface` + `np.transpose`. Also, prefer OpenCV's `resize` over Pygame's `transform`.
