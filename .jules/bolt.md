## 2026-09-30 - Pygame Surface Creation Optimization
**Learning:** In Pygame, creating surfaces from numpy arrays using `pygame.surfarray.make_surface` coupled with `np.transpose` is significantly slower than converting the array to bytes and using `pygame.image.frombuffer`. Native OpenCV resizing before Pygame surface creation also drastically reduces overhead.
**Action:** Always resize frames with `cv2.resize` first, then use `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')` for video frame rendering to maximize performance (10-15x faster).
