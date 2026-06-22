## 2024-05-14 - [Video Rendering Optimization]
 **Learning:** Replacing `pygame.surfarray.make_surface` and `pygame.transform.smoothscale` with `cv2.resize` and `pygame.image.frombuffer` results in a ~3.85x speedup for video frame rendering.
 **Action:** Apply this optimization to both `engine/video_frame_reader.py` and `engine/cutscene_player.py`. Ensure we use `np.ascontiguousarray` before `frombuffer`.
