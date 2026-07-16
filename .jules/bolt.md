## 2024-07-16 - Pygame Surface Creation Optimization
**Learning:** Pygame `pygame.surfarray.make_surface` requires `np.transpose` because OpenCV outputs shape as `(height, width)` but Pygame expects `(width, height)`. Both operations (`np.transpose` + `make_surface`) are slow.
**Action:** Use `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` directly on contiguous memory. This is a zero-copy operation that avoids the expensive transpose and array copy entirely. The frame needs to be contiguous (`np.ascontiguousarray` is already done in `_process_frame` or can be added). Size tuple must be `(width, height)`.

## 2024-07-16 - CV2 Resize + FromBuffer Optimization
**Learning:** Pygame's `smoothscale` is much slower than OpenCV's `resize`. Combined with the `pygame.image.frombuffer` optimization, performing `cv2.resize` first and then converting to a surface drops processing time significantly (from ~2s to ~0.1s for 100 frames).
**Action:** Replace `cv2.cvtColor` -> `np.transpose` -> `pygame.surfarray.make_surface` -> `pygame.transform.smoothscale` pipeline with `cv2.resize` -> `cv2.cvtColor` -> `np.ascontiguousarray` -> `pygame.image.frombuffer`. Note: resize should happen *before* cvtColor for slightly better cache locality, and `ascontiguousarray` is needed because slicing/resizing might affect memory contiguity.
