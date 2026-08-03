## 2024-05-18 - Optimize Pygame + OpenCV video frame rendering
**Learning:** `pygame.transform.smoothscale`, `np.transpose` and `pygame.surfarray.make_surface` are bottlenecks for translating OpenCV BGR arrays to Pygame surfaces.
**Action:** Use `cv2.resize` on the BGR frame *before* converting to RGB for maximum efficiency (reduces size of array to iterate during conversion). Then, map the contiguous ndarray directly to a Pygame Surface using `pygame.image.frombuffer(rgb.data, (rgb.shape[1], rgb.shape[0]), "RGB")` to avoid costly memory copies and transposes.
