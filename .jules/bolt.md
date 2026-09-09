
## 2024-05-18 - [Pygame Video Rendering Optimization]
**Learning:** `pygame.surfarray.make_surface` requires an expensive `np.transpose` because Pygame and NumPy use different axis orders. Pygame's `frombytes` with `tobytes()` is significantly faster. Furthermore, using `cv2.resize` on the BGR frame before color conversion is over 2x faster than `pygame.transform.smoothscale` on the resulting Surface.
**Action:** Replace `np.transpose` and `surfarray.make_surface` with `pygame.image.frombytes`. Always perform image resizing with `cv2.resize` prior to converting to a Pygame Surface.
