#!/usr/bin/env python3
"""Package the compiled Flash client for Ubuntu desktops with Wine."""
from pathlib import Path
import shutil
import subprocess
import tarfile
import sys
import argparse
import shlex
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.game_config import apply_resources, load_config
from backend.server import STATIC_PAGES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild-worker", action="store_true", help="Recompile the worker from sibling server source")
    parser.add_argument("--archive-only", action="store_true", help="Build the portable archive without Debian packaging tools")
    parser.add_argument("--server-url", help="Include a play-online.sh launcher for this server")
    args = parser.parse_args()
    if args.server_url:
        endpoint = urlsplit(args.server_url)
        if endpoint.scheme not in ('http','https') or not endpoint.hostname or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
            parser.error('--server-url must be an HTTP(S) URL without credentials, query or fragment')
    root = Path(__file__).resolve().parent.parent
    config = load_config()
    build = root / "linux/build"
    bundle = build / "BoufbowlOffline"
    if bundle.exists():
        shutil.rmtree(bundle)
    bundle.mkdir(parents=True)
    bun = shutil.which("bun") or str(Path.home() / ".bun/bin/bun")
    if args.rebuild_worker:
        subprocess.run([bun, str(root / "backend/build-worker.ts")], check=True)
        shutil.copy2(root / "backend/engine_base.json", root / "backend/build/engine_base.json")
    if not (root / "backend/build/engine.js").is_file() or not (root / "backend/build/engine_base.json").is_file():
        parser.error("Compiled worker missing: update the checkout, or use --rebuild-worker with sibling server source available")
    for name in ("bin", "assets", "resources", "tools", "protocol", "backend", "docs"):
        shutil.copytree(root / name, bundle / name,
                        ignore=shutil.ignore_patterns(".tutorial-build-*", "__pycache__"))
    apply_resources(bundle / "resources", config)
    (bundle / "backend/runtime").mkdir(exist_ok=True)
    shutil.copy2(bun, bundle / "backend/runtime/bun")
    for name in ("play.py", "play.sh", "README.md", *STATIC_PAGES):
        shutil.copy2(root / name, bundle / name)
    (bundle / "README.txt").write_text(
        "Boufbowl Offline for Linux\n\n"
        "Requires Python 3, Wine (including 32-bit support), and X11/XWayland.\n"
        "Run ./play.sh from a graphical desktop.\n"
        "Use ./play.sh --mode tutorial to enter the tutorial directly.\n"
        "Run ./play.sh --mode server for accounts, persistent clubs and human/CPU matches.\n"
        "Server > Community opens friends, rankings, history, replays, spectating and chat.\n"
        "The local backend and Bun simulation runtime are bundled.\n"
        "For LAN/Android: python3 -m backend.server --host 0.0.0.0 --port 9900\n")
    if args.server_url:
        launcher = bundle / 'play-online.sh'
        launcher.write_text('#!/bin/sh\ncd "$(dirname "$0")" || exit 1\nexec ./play.sh --mode server --server-url '+shlex.quote(args.server_url)+' "$@"\n')
        launcher.chmod(0o755)
        with (bundle / 'README.txt').open('a') as instructions:
            instructions.write('\nOnline play: run ./play-online.sh to connect to '+args.server_url+'\n')

    archive = build / "BoufbowlOffline-linux.tar.gz"
    temporary_archive = archive.with_name("." + archive.name + ".building")
    with tarfile.open(temporary_archive, "w:gz") as output:
        output.add(bundle, arcname=bundle.name)
    temporary_archive.replace(archive)

    if args.archive_only:
        print("Built", archive)
        return

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
