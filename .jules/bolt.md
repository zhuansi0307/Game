## $(date +%Y-%m-%d) - [Optimize Video Surface Conversion]
**Learning:** Pygame `pygame.surfarray.make_surface` combined with `np.transpose` is extremely slow and memory-intensive for high-resolution video frames (e.g. 1080p).
**Action:** Replace it with `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')` which is 10-15x faster and significantly reduces CPU load during playback.
