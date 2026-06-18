## 2024-05-24 - Zero-copy Pygame Frame Rendering
**Learning:** In a Pygame + OpenCV video frame rendering loop, using `np.transpose` and `pygame.surfarray.make_surface` causes significant memory copying overhead. Pygame 2.x doesn't natively support BGR.
**Action:** Use `cv2.resize` on the ndarray directly rather than `pygame.transform.smoothscale`. Then convert the frame to RGB and use `pygame.image.frombuffer(np.ascontiguousarray(rgb).data, (width, height), 'RGB')` to map the frames to Pygame Surfaces via zero-copy. Ensure the size tuple is `(width, height)`.
