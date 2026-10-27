## 2024-05-18 - Video frame rendering optimizations
**Learning:** Pygame surface creation using `pygame.image.frombuffer(array.tobytes(), (width, height), 'RGB')` combined with pre-resizing via OpenCV before color conversion and surface creation is extremely fast (approx. 4-5x faster than the `pygame.surfarray.make_surface` + `np.transpose` + `pygame.transform.smoothscale` approach).
**Action:** Use this optimized method for video frame rendering in `engine/video_frame_reader.py` and `engine/cutscene_player.py`.
