"""Encode website stadium previews and the transparent site logo as AVIF."""
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
QUALITY = 80


def encode_png(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "avifenc", "--qcolor", str(QUALITY), "--qalpha", str(QUALITY),
        "--speed", "6", str(source), str(target),
    ], check=True)


def main():
    manifest = json.loads((ROOT / "resources/stadium_art.json").read_text())
    for texture in manifest["textures"].values():
        source = ROOT / texture["path"]
        target = ROOT / texture["web_path"]
        encode_png(source, target)
        print(f"{source.relative_to(ROOT)} -> {target.relative_to(ROOT)} ({QUALITY}% quality)")

    logo = ROOT / "assets/site/logo.webp"
    with tempfile.TemporaryDirectory(prefix="site-logo-avif-") as temporary:
        png = Path(temporary) / "logo.png"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-i", str(logo),
            "-frames:v", "1", str(png),
        ], check=True)
        target = ROOT / "assets/site/logo.avif"
        encode_png(png, target)
    print(f"{logo.relative_to(ROOT)} -> assets/site/logo.avif ({QUALITY}% quality, alpha preserved)")


if __name__ == "__main__":
    main()
