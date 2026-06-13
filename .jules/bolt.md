## 2024-05-24 - Pygame Surface Creation from OpenCV Arrays

**Learning:** `pygame.image.frombuffer` combined with `np.ascontiguousarray` is drastically faster (1000x) than `np.transpose` + `pygame.surfarray.make_surface` for mapping OpenCV BGR/RGB arrays to Pygame surfaces. Also, `cv2.resize` on the numpy array is 10x faster than `pygame.transform.smoothscale`.

**Action:** Whenever working with Pygame and OpenCV together, use `cv2.cvtColor` + `cv2.resize` on the numpy array, then `np.ascontiguousarray` and `pygame.image.frombuffer` with 'RGB' to avoid massive copying/transposing overhead.
