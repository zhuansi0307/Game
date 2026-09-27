## 2024-05-19 - Pygame + OpenCV Surface Conversion Bottleneck
**Learning:** The traditional approach of using `pygame.surfarray.make_surface(np.transpose(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), (1, 0, 2)))` is incredibly slow, acting as a massive bottleneck for video playback frame rates.
**Action:** Always resize OpenCV frames first using `cv2.resize()`, then convert to RGB and use `pygame.image.frombuffer(array.tobytes(), size, 'RGB')` which bypasses the expensive `transpose` and `make_surface` overhead for a 10-20x speedup.
