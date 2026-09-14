
## 2024-05-18 - Optimize Pygame Video Frame Processing
**Learning:** In Pygame + OpenCV integrations, using `np.transpose` followed by `pygame.surfarray.make_surface` for video frames is extremely slow and can lead to use-after-free bugs when local arrays are garbage collected. Furthermore, performing `cv2.cvtColor` before resizing or scaling means processing far more pixels than necessary.
**Action:** Use `pygame.image.frombytes(array.tobytes(), (width, height), 'RGB')` instead. It safely copies memory, completely bypasses the need for the slow `np.transpose`, and prevents memory-sharing crashes. Always perform `cv2.resize` on the BGR ndarray before converting it to RGB to minimize color-space conversion overhead.
