## 2026-08-31 - [Video Frame Conversion Optimization]
**Learning:** Pygame's `surfarray.make_surface` combined with OpenCV's `cvtColor` and `np.transpose` causes unnecessary allocations and data copies.
**Action:** Use OpenCV's highly optimized `resize` function before `cvtColor`, ensure contiguous arrays, and use zero-copy `pygame.image.frombuffer` to efficiently bridge the data.
