## 2024-05-18 - Video rendering optimizations
**Learning:** Pygame surface creation from numpy arrays is slow with `pygame.surfarray.make_surface` + `np.transpose`. Using `pygame.image.frombuffer(array.tobytes(), (width, height), "RGB")` is much faster. Also resizing the frame using `cv2.resize` natively with OpenCV before doing color space conversions is much faster.
**Action:** Use `pygame.image.frombuffer` and do OpenCV manipulations before color/space conversions.
