"""Convert the preserved tutorial FLVs into the homepage's browser media."""
from pathlib import Path
import subprocess
import tempfile

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
    target = output / "tutorial-poster.avif"
    with tempfile.TemporaryDirectory(prefix="tutorial-poster-") as temporary:
        frame = Path(temporary) / "poster.png"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "1", "-i",
                        str(ROOT / "assets/videos/layout_tuto_01.flv"), "-frames:v", "1",
                        str(frame)], check=True)
        building = target.with_name(target.stem + ".building.avif")
        subprocess.run(["avifenc", "--qcolor", "80", "--qalpha", "80", "--speed", "6",
                        str(frame), str(building)], check=True)
        building.replace(target)
    print("Generated tutorial videos and poster from preserved FLVs")


if __name__ == "__main__":
    main()
