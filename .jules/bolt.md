## 2025-02-28 - Pygame Surface conversion optimization
**Learning:** In Pygame, converting an OpenCV NumPy array to a Pygame Surface using `np.transpose` + `pygame.surfarray.make_surface` is extremely slow (~10ms per 1080p frame) because it creates copies and does heavy data manipulation. Using `pygame.image.frombuffer(frame.data, (frame.shape[1], frame.shape[0]), 'RGB')` is essentially zero-copy and orders of magnitude faster (~2µs).
**Action:** Always use `pygame.image.frombuffer` directly on contiguous memory for video frame conversions in Pygame.
