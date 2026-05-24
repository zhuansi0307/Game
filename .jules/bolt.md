
## 2024-06-03 - Pygame OpenCV Video Frame Rendering Optimization
**Learning:** Pygame `surfarray.make_surface` combined with `np.transpose` is extremely slow and acts as a huge bottleneck for video frame rendering. `pygame.image.frombuffer` offers a zero-copy fast path but requires an RGB contiguous array. Also, using OpenCV `cv2.resize` on the ndarray is faster than `pygame.transform.smoothscale`.
**Action:** When converting OpenCV frames to Pygame Surfaces in this codebase, ALWAYS use `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` with an `np.ascontiguousarray` RGB frame instead of `np.transpose` and `surfarray.make_surface`.
