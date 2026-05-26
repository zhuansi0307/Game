## 2024-05-24 - Pygame Video Optimization
**Learning:** Pygame image conversion is slow. Avoid np.transpose and pygame.surfarray.make_surface by using pygame.image.frombuffer.
**Action:** When optimizing video rendering with OpenCV and Pygame, use pygame.image.frombuffer(frame, size, 'RGB') and cv2.resize directly on the frame to minimize data copying and transformation overhead.
