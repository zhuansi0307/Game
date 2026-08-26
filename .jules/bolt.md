## 2024-05-24 - Pygame Video Rendering Optimization
**Learning:** In Pygame with OpenCV, `pygame.surfarray.make_surface` and `np.transpose` are significantly slower than mapping the contiguous OpenCV array directly to a surface. Also, `cv2.resize` is much faster than `pygame.transform.smoothscale`.
**Action:** Use `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` on a contiguous RGB ndarray instead of `np.transpose` and `make_surface`. Resize with `cv2.resize` *before* `cvtColor`.
