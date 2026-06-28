## 2024-05-15 - Zero-copy Pygame Surface creation for video frames
**Learning:** In a Pygame + OpenCV app, using `np.transpose` and `pygame.surfarray.make_surface` to convert OpenCV BGR/RGB arrays to Pygame Surfaces is very expensive (involves memory copying and array manipulation).
**Action:** Use `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` instead to map the contiguous OpenCV RGB array directly into a Pygame Surface without extra copying. This achieved a ~27x speedup for surface creation.
