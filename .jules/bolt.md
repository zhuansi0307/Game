## 2024-05-18 - [Zero-copy OpenCV to Pygame conversion]
**Learning:** `pygame.surfarray.make_surface` + `np.transpose` is incredibly slow for 1080p frames (takes ~10ms per frame).
**Action:** Use `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` instead, taking care to use `np.ascontiguousarray` if the buffer is sliced or resized, which is near-instantaneous. Make sure the dimensions are passed as `(width, height)`.

## 2024-05-18 - [Pygame headlessly in CI]
**Learning:** Pygame throws ALSA errors and fails to init properly headlessly unless wrapped with `xvfb-run -a`.
**Action:** Use `xvfb-run -a python script.py` for testing Pygame code without a display.
