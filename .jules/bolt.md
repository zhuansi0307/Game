## 2024-05-18 - [Optimize Pygame Surface Creation from OpenCV]
**Learning:** `pygame.surfarray.make_surface` coupled with `np.transpose` is extremely slow compared to `pygame.image.frombuffer` on a contiguous array for video frame rendering.
**Action:** Use `cv2.resize` on the array directly if resizing is needed, ensure array is contiguous (`np.ascontiguousarray`), and use `pygame.image.frombuffer(array.data, (array.shape[1], array.shape[0]), 'RGB')`.
