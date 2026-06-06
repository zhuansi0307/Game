## 2024-05-17 - Pygame Video Rendering Bottleneck
**Learning:** In Pygame, converting OpenCV frames (NumPy arrays) to Surfaces using `np.transpose` and `pygame.surfarray.make_surface` is incredibly slow due to memory copying and reshaping.
**Action:** Use `pygame.image.frombuffer(np.ascontiguousarray(frame).data, size, 'RGB')` instead. This directly maps the contiguous C array to the Pygame surface, preventing memory copying and resulting in thousands of times faster execution per frame.
