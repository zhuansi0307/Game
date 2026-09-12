## 2023-10-27 - [Video Rendering Optimization]
**Learning:** For Pygame + OpenCV video frame rendering, using `pygame.surfarray.make_surface` with `np.transpose` is highly inefficient and risks memory safety issues when the numpy array is local. Resizing after converting to RGB is also less efficient.
**Action:** Use `cv2.resize` directly on the BGR ndarray, then `cv2.cvtColor`, and finally copy to a surface safely and quickly using `pygame.image.frombytes(array.tobytes(), (width, height), 'RGB')`.
