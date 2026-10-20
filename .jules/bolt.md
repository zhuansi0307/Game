## 2024-03-08 - [Video Frame Processing Optimization]
**Learning:** For Pygame + OpenCV video frame rendering, `pygame.surfarray.make_surface` + `np.transpose` is extremely slow. Using `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')` is 10-15x faster. Also, performing OpenCV `cv2.resize` on the source `ndarray` *before* `cv2.cvtColor` minimizes the amount of pixel processing needed.
**Action:** Always use `pygame.image.frombuffer` for bulk surface conversions, and resize frames natively with OpenCV before changing color spaces.
