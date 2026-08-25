
## 2026-08-25 - Pygame Zero-Copy Video Frame Render Optimization
**Learning:** OpenCV to Pygame frame conversion is a major bottleneck due to `np.transpose` and `pygame.surfarray.make_surface` triggering expensive memory copying and reallocations. Additionally, `cv2.resize` is much more performant when executed on the BGR ndarray before converting it to RGB.
**Action:** Always resize first in BGR. When converting OpenCV output to Pygame surfaces, convert BGR->RGB, ensure array contiguousness (`np.ascontiguousarray`), and use `pygame.image.frombuffer(frame.data, (frame.shape[1], frame.shape[0]), 'RGB')` for zero-copy performance mapping directly to the underlying Surface pointer.
