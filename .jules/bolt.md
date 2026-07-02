## 2024-05-24 - Pygame Video Rendering Bottleneck
**Learning:** `pygame.surfarray.make_surface` + `np.transpose` is significantly slower than `pygame.image.frombuffer` for rendering video frames in Pygame. Additionally, `pygame.transform.smoothscale` is slower than `cv2.resize`.
**Action:** Always use `pygame.image.frombuffer(frame.data, (width, height), 'RGB')` with contiguous arrays instead of `make_surface` + `np.transpose`, and prefer `cv2.resize` over `pygame.transform.smoothscale`.
