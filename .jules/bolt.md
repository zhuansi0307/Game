## 2024-05-18 - [Pygame Video Frame Rendering Optimization]
**Learning:** Pygame's `surfarray.make_surface` coupled with `np.transpose` is slow for video playback. `pygame.image.frombuffer` avoids unnecessary data copying and transposing when processing OpenCV frames.
**Action:** Always prefer `pygame.image.frombuffer` and `np.ascontiguousarray` for fast OpenCV frame to Pygame Surface conversion.
