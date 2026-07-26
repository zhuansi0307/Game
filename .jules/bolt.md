## 2024-05-18 - [Pygame Surface Conversion Performance]
**Learning:** `pygame.surfarray.make_surface` combined with `np.transpose` is significantly slower (by a factor of ~4000x for 1080p frames) compared to `pygame.image.frombuffer` on a contiguous array.
**Action:** Replace `make_surface` and `transpose` with `pygame.image.frombuffer(frame.data, (frame.shape[1], frame.shape[0]), 'RGB')` (ensuring frame is contiguous) for optimal video frame rendering in `engine/video_frame_reader.py` and `engine/cutscene_player.py`.
