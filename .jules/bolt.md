## 2024-05-24 - [Pygame Surface Creation Bottleneck]
**Learning:** In Pygame, creating surfaces from numpy arrays using `pygame.surfarray.make_surface` combined with `np.transpose` is highly inefficient and creates a bottleneck during video playback.
**Action:** Always use `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')` which is significantly faster (10-15x) for video frame processing. Additionally, always perform OpenCV operations like `cv2.resize` on the original array before `cv2.cvtColor` to minimize pixel processing overhead.
