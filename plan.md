1. Modify `engine/video_frame_reader.py` and `engine/cutscene_player.py` to optimize video frame processing:
    - Instead of `np.transpose` and `pygame.surfarray.make_surface`, use the faster `pygame.image.frombuffer(frame.tobytes(), (width, height), 'RGB')`.
    - In `video_frame_reader.py`, the `_frame_to_surface` function currently does:
      ```python
      surface_array = np.transpose(frame, (1, 0, 2))
      return pygame.surfarray.make_surface(surface_array)
      ```
      Replace it with:
      ```python
      height, width = frame.shape[:2]
      return pygame.image.frombuffer(frame.tobytes(), (width, height), 'RGB')
      ```
    - Also in `video_frame_reader.py`, the `_process_frame` function currently converts color, gets shape, then resizes. Change it to resize first, then convert color to minimize pixel processing, returning the `np.ascontiguousarray` of the result.
      ```python
      height, width = frame.shape[:2]
      target_width, target_height = self.target_size
      if (width, height) != self.target_size:
          interpolation = cv2.INTER_AREA if width > target_width or height > target_height else cv2.INTER_LINEAR
          frame = cv2.resize(frame, self.target_size, interpolation=interpolation)
      rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
      return np.ascontiguousarray(rgb_frame)
      ```
    - In `cutscene_player.py`, update `_get_video_frame` accordingly:
      ```python
      rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
      height, width = rgb.shape[:2]
      surface = pygame.image.frombuffer(rgb.tobytes(), (width, height), 'RGB')
      ```
2. Verify the changes using a test script.
3. Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.
