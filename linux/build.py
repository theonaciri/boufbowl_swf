#!/usr/bin/env python3
"""Package the compiled Flash client for Ubuntu desktops with Wine."""
from pathlib import Path
import shutil
import subprocess
import tarfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.game_config import apply_resources, load_config


def main():
    root = Path(__file__).resolve().parent.parent
    config = load_config()
    build = root / "linux/build"
    bundle = build / "BoufbowlOffline"
    if bundle.exists():
        shutil.rmtree(bundle)
    bundle.mkdir(parents=True)
    bun = shutil.which("bun") or str(Path.home() / ".bun/bin/bun")
    subprocess.run([bun, "build", str(root / "backend/engine.ts"), "--target=bun", "--outfile=" + str(root / "backend/build/engine.js")], check=True)
    shutil.copy2(root / "backend/engine_base.json", root / "backend/build/engine_base.json")
    for name in ("bin", "assets", "resources", "tools", "protocol", "backend", "docs"):
        shutil.copytree(root / name, bundle / name,
                        ignore=shutil.ignore_patterns(".tutorial-build-*", "__pycache__"))
    apply_resources(bundle / "resources", config)
    (bundle / "backend/runtime").mkdir(exist_ok=True)
    shutil.copy2(bun, bundle / "backend/runtime/bun")
    for name in ("play.py", "play.sh", "README.md"):
        shutil.copy2(root / name, bundle / name)
    (bundle / "README.txt").write_text(
        "Boufbowl Offline for Linux\n\n"
        "Requires Python 3, Wine (including 32-bit support), and X11/XWayland.\n"
        "Run ./play.sh from a graphical desktop.\n"
        "Use ./play.sh --mode tutorial to enter the tutorial directly.\n"
        "Run ./play.sh --mode server for persistent clubs and CPU matches.\n"
        "The local backend and Bun simulation runtime are bundled.\n"
        "For LAN/Android: python3 -m backend.server --host 0.0.0.0 --port 9900\n")
    archive = build / "BoufbowlOffline-linux.tar.gz"
    with tarfile.open(archive, "w:gz") as output:
        output.add(bundle, arcname=bundle.name)

    package = build / "deb"
    if package.exists():
        shutil.rmtree(package)
    shutil.copytree(bundle, package / "opt/boufbowl-offline")
    (package / "DEBIAN").mkdir()
    (package / "DEBIAN/control").write_text(
        "Package: boufbowl-offline\nVersion: 1.0.0\nSection: games\n"
        "Priority: optional\nArchitecture: amd64\n"
        "Maintainer: Boufbowl Offline <boufbowl@localhost>\n"
        "Depends: python3, wine, wine32\n"
        "Description: Boufbowl client and persistent replacement game server\n"
        " Runs the original patched Flash client through Wine.\n")
    applications = package / "usr/share/applications"
    applications.mkdir(parents=True)
    (applications / "boufbowl-offline.desktop").write_text(
        "[Desktop Entry]\nType=Application\nName=Boufbowl Offline\n"
        "Exec=/opt/boufbowl-offline/play.sh\nTerminal=false\nCategories=Game;\n")
    deb = build / "BoufbowlOffline-linux-amd64.deb"
    subprocess.run(["dpkg-deb", "--root-owner-group", "--build", package, deb], check=True)
    print("Built", archive)
    print("Built", deb)


if __name__ == "__main__":
    main()
