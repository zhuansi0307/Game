## 2024-05-30 - [Pygame Surface Creation Optimization]
**Learning:** For Pygame + OpenCV video frame rendering optimization, `pygame.surfarray.make_surface` and `np.transpose` are significantly slower than using `pygame.image.frombytes(array.tobytes(), (width, height), 'RGB')`. The memory copy prevents the use-after-free bug that `pygame.image.frombuffer` has with local numpy arrays.
**Action:** Replace `np.transpose` and `pygame.surfarray.make_surface` with `pygame.image.frombytes` in video processing loops to speed up frame rendering.
