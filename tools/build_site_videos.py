"""Convert the preserved tutorial FLVs into the homepage's browser media."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def main():
    output = ROOT / "assets/site"
    output.mkdir(parents=True, exist_ok=True)
    for source, name in (("tutorial-intro.flv", "tutorial-archive.mp4"),
                         ("layout_tuto_01.flv", "tutorial-field.mp4")):
        target = output / name
        temporary = target.with_name(target.stem + ".building.mp4")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(ROOT / "assets/videos" / source),
                        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(temporary)], check=True)
        temporary.replace(target)
    target = output / "tutorial-poster.webp"
    temporary = target.with_name(target.stem + ".building.webp")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "1", "-i",
                    str(ROOT / "assets/videos/layout_tuto_01.flv"), "-frames:v", "1",
                    "-c:v", "libwebp", "-quality", "95", str(temporary)], check=True)
    temporary.replace(target)
    print("Generated tutorial videos and poster from preserved FLV inputs")


if __name__ == "__main__":
    main()
