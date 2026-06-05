
## 2024-06-05 - [Pygame Video Frame Optimization]
**Learning:** `pygame.surfarray.make_surface` coupled with `np.transpose` is a major performance bottleneck for rendering video frames from OpenCV to Pygame due to memory copying and transposing. `pygame.transform.smoothscale` is also significantly slower than `cv2.resize`.
**Action:** Use `pygame.image.frombuffer(frame.data, size, 'RGB')` for zero-copy surface creation from contiguous numpy arrays. Use `cv2.resize` instead of `pygame.transform.smoothscale` for resizing frames before converting them to surfaces.
