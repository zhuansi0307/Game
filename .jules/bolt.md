## 2024-05-24 - Zero-copy Pygame Surface Creation
**Learning:** Pygame `surfarray.make_surface` involves transposing an array and making a copy of data, which is slow for full HD video frames.
**Action:** Use `pygame.image.frombuffer` with contiguous RGB ndarray data and the correct size tuple to avoid transposing and copying data.
