## 2024-06-12 - Pygame rendering bottlenecks
**Learning:** `np.transpose` and `pygame.surfarray.make_surface` and `pygame.transform.smoothscale` are massive bottlenecks for real-time video frame rendering in Pygame compared to native OpenCV scaling and `pygame.image.frombuffer` sharing.
**Action:** Use `np.ascontiguousarray` combined with `pygame.image.frombuffer(data, (width, height), 'RGB')` and `cv2.resize` instead of Pygame's smoothscale for any real-time buffer passing from cv2/numpy to Pygame surfaces to avoid expensive copy operations.
