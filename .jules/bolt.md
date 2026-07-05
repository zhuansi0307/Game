## 2024-07-05 - Pygame Video Frame Rendering Optimization
**Learning:** `pygame.surfarray.make_surface` combined with `np.transpose` is significantly slower than using `pygame.image.frombuffer(contiguous_array.data, (width, height), 'RGB')`. By resizing the OpenCV array using `cv2.resize` and converting it to a contiguous array, we can map it to a Pygame Surface with zero-copy buffer, bypassing expensive transpositions.
**Action:** Use `pygame.image.frombuffer` for rendering OpenCV frames in Pygame, ensuring the array is contiguous and sizes are passed as `(width, height)`.
