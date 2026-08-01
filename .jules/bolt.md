
## 2024-05-18 - [Pygame + OpenCV zero-copy rendering pattern]
**Learning:** Pygame's `surfarray.make_surface` combined with `np.transpose` is highly inefficient and caused massive performance bottlenecks in video frame rendering. `pygame.transform.smoothscale` is also slower than OpenCV's `cv2.resize`.
**Action:** Use `pygame.image.frombuffer(frame.data, (frame.shape[1], frame.shape[0]), 'RGB')` with contiguous arrays for zero-copy surface creation. Also, perform resizing using `cv2.resize` on the raw BGR frame *before* color conversion.
