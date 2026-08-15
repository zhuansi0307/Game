
## 2024-05-18 - [Zero-Copy Pygame Surfaces from OpenCV]
**Learning:** By default, using `np.transpose()` and `pygame.surfarray.make_surface()` to convert OpenCV BGR frames to Pygame RGB surfaces is extremely expensive due to full array copies and slow Python-side data iteration.
**Action:** Always use `pygame.image.frombuffer(frame.data, (frame.shape[1], frame.shape[0]), 'RGB')` in this codebase for converting OpenCV frames to Pygame. This is a zero-copy operation. Ensure the frame is resized natively in OpenCV (C++) *before* converting color space to minimize the number of pixels processed.
