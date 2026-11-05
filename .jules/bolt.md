## 2025-05-18 - [Optimize Video Frame Pygame Surface Conversion]
**Learning:** `pygame.surfarray.make_surface` + `np.transpose` is 10-15x slower for converting OpenCV ndarrays to Pygame surfaces than `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')`.
**Action:** Replace `make_surface` and `transpose` with `pygame.image.frombuffer(rgb.tobytes(), (rgb.shape[1], rgb.shape[0]), 'RGB')` wherever OpenCV arrays need to be converted to Pygame surfaces.

## 2025-05-18 - [Optimize Video Frame Pygame Surface Conversion + Resizing]
**Learning:** Resizing the video frame with `cv2.resize` natively before `cv2.cvtColor` and `pygame.image.frombuffer` is about 12x faster than using `pygame.surfarray.make_surface` followed by `pygame.transform.smoothscale`. This avoids expensive processing in Python space and handles scaling before allocating Pygame surfaces.
**Action:** Always resize frames using `cv2.resize(frame, (SCREEN_WIDTH, SCREEN_HEIGHT))` before creating a Pygame Surface. Use `pygame.image.frombuffer` on the resized bytes.
