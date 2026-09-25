## 2024-05-20 - [Video Frame Processing Optimization]
**Learning:** For Pygame + OpenCV video frame rendering, using `cv2.resize` directly on the `ndarray` *before* color conversion is measurably faster than performing color conversion first.
**Action:** Always resize frames natively with OpenCV before converting colors to minimize overhead since resizing on a larger image takes more time and color converting a larger image also takes more time.

## 2024-05-20 - [Video Frame Surface Creation Optimization]
**Learning:** For Pygame surface creation from numpy arrays, using `pygame.image.frombuffer(array.tobytes(), size, 'RGB')` is extremely fast (10-15x faster than `pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))`).
**Action:** Use `frombuffer` + `tobytes` instead of array transposition and `make_surface` when converting numpy image frames to Pygame surfaces.
