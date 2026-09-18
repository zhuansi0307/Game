
## 2024-05-18 - [Optimize Pygame Frame Creation]
**Learning:** For Pygame + OpenCV video frame rendering, using `pygame.image.frombuffer` or `pygame.surfarray.make_surface` alongside local variable arrays shares memory and causes use-after-free vulnerabilities when the numpy array is garbage collected. Doing `.transpose` is also extremely slow.
**Action:** Use `pygame.image.frombytes(array.tobytes(), (width, height), 'RGB')` to safely and quickly copy the memory. Do not use `pygame.transform.smoothscale` for resizing, as it performs poorly; instead prefer `cv2.resize` natively on the ndarray before converting it.
