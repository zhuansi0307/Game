## 2026-10-19 - Optimize Video Frame Processing
**Learning:** In Pygame + OpenCV video rendering, `cv2.cvtColor` followed by `np.transpose` and `pygame.surfarray.make_surface` is extremely slow. Also, resizing after color conversion is suboptimal because you process more channels and unneeded pixels.
**Action:** Always resize first using `cv2.resize`, then convert color using `cv2.cvtColor`, then use `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')` for 10-15x faster frame-to-surface conversion.
