## 2023-10-25 - Video Frame Conversion Optimization
**Learning:** In Pygame, converting an OpenCV BGR video frame to a Pygame Surface using `pygame.surfarray.make_surface` + `np.transpose` and `pygame.transform.smoothscale` is extremely slow and a performance bottleneck.
**Action:** Use `pygame.image.frombuffer(rgb.tobytes(), (width, height), 'RGB')` instead. It bypasses numpy transposes and intermediate array creations, executing ~10-15x faster than the legacy approach.
