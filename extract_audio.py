import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import imageio_ffmpeg
except ImportError:
    print("imageio-ffmpeg is not installed")
    sys.exit(1)


ROOT_DIR = Path(__file__).resolve().parent
ASSETS_DIR = ROOT_DIR / "assets"
STANDARD_ASSET_DIRS = {"audio", "bg", "fonts", "ui", "videos"}


def iter_video_dirs():
    videos_dir = ASSETS_DIR / "videos"
    if videos_dir.exists():
        yield videos_dir

    for child in ASSETS_DIR.iterdir():
        if child.is_dir() and child.name not in STANDARD_ASSET_DIRS:
            yield child


def summarize_error(stderr):
    text = stderr.strip().replace("\r", "")
    if not text:
        return "unknown ffmpeg error"
    lines = [line for line in text.split("\n") if line.strip()]
    return lines[-1] if lines else text


def extract_audio(ffmpeg_exe, mp4_file):
    mp3_file = mp4_file.with_suffix(".mp3")
    if mp3_file.exists():
        print(f"Skip existing: {mp3_file}")
        return "skipped"

    with tempfile.TemporaryDirectory(prefix="sg_audio_") as temp_dir:
        temp_dir = Path(temp_dir)
        temp_video = temp_dir / "input.mp4"
        temp_audio = temp_dir / "output.mp3"
        shutil.copy2(mp4_file, temp_video)

        cmd = [
            ffmpeg_exe,
            "-hide_banner",
            "-y",
            "-i",
            str(temp_video),
            "-vn",
            "-acodec",
            "libmp3lame",
            "-ar",
            "44100",
            "-b:a",
            "192k",
            str(temp_audio),
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if result.returncode != 0 or not temp_audio.exists() or temp_audio.stat().st_size == 0:
            error = summarize_error(result.stderr)
            if "does not contain any stream" in result.stderr or "Stream map" in result.stderr:
                print(f"No audio track: {mp4_file}")
                return "no_audio"
            print(f"Failed: {mp4_file} -> {error}")
            return "failed"

        shutil.copy2(temp_audio, mp3_file)
        print(f"Success: {mp4_file} -> {mp3_file}")
        return "success"


def main():
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    counts = {"success": 0, "skipped": 0, "no_audio": 0, "failed": 0}

    mp4_files = []
    for video_dir in iter_video_dirs():
        mp4_files.extend(sorted(video_dir.rglob("*.mp4")))

    for mp4_file in mp4_files:
        status = extract_audio(ffmpeg_exe, mp4_file)
        counts[status] += 1

    print("Audio extraction complete.")
    print(
        "Summary: "
        f"success={counts['success']}, "
        f"skipped={counts['skipped']}, "
        f"no_audio={counts['no_audio']}, "
        f"failed={counts['failed']}"
    )

    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
