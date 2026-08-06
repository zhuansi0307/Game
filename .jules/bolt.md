## 2024-08-06 - [Optimize Pygame frame rendering from OpenCV array]
**Learning:** In this codebase, creating Pygame surfaces from OpenCV frames using `np.transpose` and `pygame.surfarray.make_surface` is an expensive zero-copy overhead. `pygame.transform.smoothscale` is also slower than `cv2.resize`.
**Action:** Use `cv2.resize` directly on the `ndarray` before color conversion. For rendering, `pygame.image.frombuffer(frame.data, (frame.shape[1], frame.shape[0]), 'RGB')` is much faster and avoids expensive transposition.
