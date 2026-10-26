## 2025-02-27 - Fast Pygame Surface Creation from OpenCV
**Learning:** Pygame `surfarray.make_surface` is extremely slow due to internal data copying, and `np.transpose` + `pygame.transform.smoothscale` adds additional massive overhead for processing video frames.
**Action:** Replace it with `cv2.resize` to do the scaling natively in C, followed by `cv2.cvtColor` to RGB, and then construct the surface instantly with `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')`. This reduces surface creation time by ~10x!
