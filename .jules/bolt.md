## 2024-10-12 - Pygame Video Rendering Optimizations
**Learning:** Converting NumPy arrays to Pygame surfaces using `pygame.image.frombuffer` is vastly faster than `surfarray.make_surface` combined with `np.transpose`. Also, resizing OpenCV frames before color conversion saves significant computation.
**Action:** Always resize first natively in OpenCV, and utilize `frombuffer` for surface creation.
