## 2023-10-27 - Pygame surface creation bottleneck
**Learning:** Pygame's `pygame.surfarray.make_surface` and `pygame.transform.smoothscale` are massive CPU bottlenecks for continuous video playback, causing significant frame drops.
**Action:** Always use OpenCV for resizing (`cv2.resize`) and `pygame.image.frombuffer` for zero-copy surface creation when rendering video frames in Pygame.
