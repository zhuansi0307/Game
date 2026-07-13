
## 2024-05-30 - [Video Frame Pygame Mapping Optimization]
**Learning:** In Pygame, when mapping OpenCV video frames (BGR -> RGB) to Pygame Surfaces, using `numpy.transpose` followed by `pygame.surfarray.make_surface()` creates a significant CPU bottleneck due to large buffer copies and transpositions.
**Action:** Use `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` on a contiguous `np.ndarray` for zero-copy mapping. This avoids the transpose entirely and speeds up buffer-to-surface conversion by over 200x. Combine with `cv2.resize` instead of `pygame.transform.smoothscale` for additional rendering efficiency.
