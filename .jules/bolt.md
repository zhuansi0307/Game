## 2024-05-24 - [Zero-Copy Frame Mapping for Pygame]
**Learning:** In this Pygame + OpenCV application, `np.transpose` and `pygame.surfarray.make_surface` create severe performance bottlenecks due to memory copies when mapping video frames. Pygame 2.x supports `pygame.image.frombuffer` which avoids copying if the array is contiguous and in RGB format.
**Action:** Use `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` and `np.ascontiguousarray` (if resized via `cv2.resize`) for all OpenCV-to-Pygame frame transfers to eliminate memory copying overhead.
