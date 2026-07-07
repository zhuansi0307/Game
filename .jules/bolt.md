## 2024-06-15 - Zero-copy Pygame Video Frames
**Learning:** `pygame.surfarray.make_surface` coupled with `np.transpose` creates a significant CPU bottleneck due to memory allocation and non-contiguous mapping when streaming OpenCV video frames into Pygame.
**Action:** Always prefer `pygame.image.frombuffer(rgb.data, (width, height), 'RGB')` coupled with `np.ascontiguousarray` for zero-copy mapping. Additionally, doing `cv2.resize` on the array *before* creating the surface is much faster than `pygame.transform.smoothscale`.
