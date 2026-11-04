
## 2024-03-20 - [Pygame Video Rendering Optimization]
**Learning:** The previous learning holds true. Optimizing `_frame_to_surface` by replacing `pygame.surfarray.make_surface` and `np.transpose` with `pygame.image.frombuffer` offers ~12.5x speedup. Furthermore, in `_process_frame`, processing `cv2.resize` BEFORE `cv2.cvtColor` gives an additional ~2x speedup by reducing the amount of pixels processed in the color space conversion step.
**Action:** Always resize first before color conversion in video processing pipelines!
