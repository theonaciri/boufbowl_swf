#!/usr/bin/env python3
"""Run Boufbowl offline menus and tutorial with Adobe Flash Player and Wine."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shutil
import subprocess
import threading


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", choices=("en", "fr", "de", "es"), default="en")
    parser.add_argument("--mode", choices=("menus", "tutorial"), default="menus")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if not shutil.which("wine"):
        parser.error("Wine is required; install it and run this launcher again.")
    data = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    state = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
    prefix = data / "boufbowl-tutorial/wine"
    logs = state / "boufbowl-tutorial"
    prefix.parent.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, WINEPREFIX=str(prefix), WINEDEBUG="-all")

    # Use XWayland on Wayland desktops; only this game's Wine prefix is affected.
    with (logs / "wine.log").open("w") as wine_log:
        subprocess.run(
            ["wine", "reg", "add", r"HKCU\Software\Wine\Drivers",
             "/v", "Graphics", "/d", "x11", "/f"],
            env=env, stdout=wine_log, stderr=subprocess.STDOUT,
            timeout=120, check=True,
        )
        with (logs / "http.log").open("w", buffering=1) as http_log:
            class Handler(SimpleHTTPRequestHandler):
                def log_message(self, fmt, *values):
                    http_log.write((fmt % values) + "\n")

            server = ThreadingHTTPServer(
                ("127.0.0.1", 0), partial(Handler, directory=str(root))
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_address[1]
            tutorial = "1" if args.mode == "tutorial" else "0"
            url = f"http://127.0.0.1:{port}/bin/boufbowl-client-1.9.6.swf?lang={args.lang}&tuto={tutorial}"
            print(f"Starting Boufbowl {args.mode} ({args.lang}). Logs: {logs}", flush=True)
            try:
                return subprocess.call(
                    ["wine", str(root / "bin/flashplayer_32_sa.exe"), url],
                    cwd=root / "bin", env=env,
                    stdout=wine_log, stderr=subprocess.STDOUT,
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
