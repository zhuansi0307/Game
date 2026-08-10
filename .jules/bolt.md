
## 2024-05-18 - [PyGame frombuffer Performance Win]
**Learning:** Rendering video frames using `pygame.image.frombuffer` along with `cv2.resize` natively (zero-copy) is much faster than doing `np.transpose` and `pygame.surfarray.make_surface` when converting OpenCV BGR frames to Pygame SURFACES. Also, temporary workflow files (`app_output.log`, `benchmark_video.py`) need to be thoroughly cleaned up before submitting.
**Action:** Next time, always clean up workflow log files and temporary scripts. Look for `np.transpose` and `make_surface` when working with PyGame + OpenCV combinations to identify easy performance wins.
