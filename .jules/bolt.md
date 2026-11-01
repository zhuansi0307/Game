
## 2023-11-01 - [Fast Pygame Video Frames]
**Learning:** Pygame `surfarray` is a major bottleneck for OpenCV video processing. Combining `pygame.image.frombuffer(array.tobytes(), size, 'RGB')` with resizing the array *before* `cv2.cvtColor` gives a 2.5x+ speedup by doing less work during color conversion and avoiding expensive numpy transpositions.
**Action:** Always resize raw BGR OpenCV frames before converting color space, and use `pygame.image.frombuffer` instead of `pygame.surfarray` for real-time video rendering in Pygame.
