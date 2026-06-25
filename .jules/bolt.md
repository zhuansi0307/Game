## 2024-05-24 - Initial Setup
**Learning:** Initializing bolt journal
**Action:** Use this file to record critical performance learnings.
## 2024-05-24 - Pygame Surface Creation Optimization
**Learning:** Pygame `pygame.surfarray.make_surface` combined with `np.transpose` is slow for 1080p video frames because it creates copies. Using `pygame.image.frombuffer` directly on the contiguous RGB numpy array is zero-copy and much faster. Note that the size argument to `frombuffer` is `(width, height)`, whereas numpy shape is `(height, width)`. Pygame requires RGB data, which OpenCV's BGR needs converting to (already happening in `_process_frame`).
**Action:** Replace `np.transpose` and `pygame.surfarray.make_surface` with `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` in `_frame_to_surface`. Ensure `frame` is contiguous.
