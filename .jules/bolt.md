## 2024-05-18 - Pygame Surface Creation Optimization
**Learning:** `pygame.surfarray.make_surface` is incredibly slow when dealing with large 1080p arrays because it requires transposing the array from `(height, width, channels)` to `(width, height, channels)` and deep copying memory. The `frombuffer` method zero-copies from raw memory and is over 4000x faster for creating surfaces from OpenCV frames.
**Action:** Use `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` instead of `np.transpose` + `pygame.surfarray.make_surface` for video frame conversion.
