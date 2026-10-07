
## $(date +%Y-%m-%d) - [Optimize Video Frame Rendering]
**Learning:** `pygame.image.frombuffer` is significantly faster (~14x in local benchmark) than `np.transpose` + `pygame.surfarray.make_surface` for converting OpenCV frames to Pygame surfaces. Additionally, applying `cv2.resize` natively on the BGR ndarray *before* color conversion to RGB minimizes pixel processing overhead.
**Action:** When working with Pygame + OpenCV, always resize frames early using `cv2.resize` and use `pygame.image.frombuffer` to create the surface directly from the memory buffer.
