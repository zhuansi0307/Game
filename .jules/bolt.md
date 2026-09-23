## 2024-05-14 - [Optimize Pygame frame extraction memory footprint]
**Learning:** Pygame's `pygame.surfarray.make_surface` coupled with `np.transpose` from local variables creates performance and memory bottlenecks, as well as a possible memory leak/crash if memory buffers from un-garbage collected arrays are shared.
**Action:** Use `pygame.image.frombytes(array.tobytes(), (width, height), 'RGB')` to safely copy the memory from OpenCV frames. Also, prefer `cv2.resize` natively on the array over `pygame.transform.smoothscale`.
