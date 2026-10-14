#!/usr/bin/env python3
"""Run Boufbowl offline menus and tutorial with Adobe Flash Player and Wine."""
import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shutil
import subprocess
import threading
from urllib.parse import parse_qs, urlsplit
from tools.game_config import load_config
from backend.server import Handler as BackendHandler, default_database
from backend.service import Service
from backend.storage import ServiceError


def main():
    config = load_config()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", choices=("en", "fr", "de", "es"), default=None, help="Override the saved game language for this launch")
    parser.add_argument("--mode", choices=("menus", "tutorial", "mock", "server"), default=config["general"]["startup_mode"])
    parser.add_argument("--server-url", help="Use a standalone backend URL instead of starting a local backend")
    parser.add_argument("--profile", help="Local device profile name (otherwise use the saved selection)")
    parser.add_argument("--database", type=Path, default=default_database())
    parser.add_argument("--fixture", type=Path, help="Replay a local protocol fixture in mock mode")
    parser.add_argument("--scene-3d", action="store_true", help="Enable the original resolution animation scene for this launch")
    args = parser.parse_args()
    language_override=args.lang is not None
    if args.lang is None: args.lang=config["general"]["language"]
    root = Path(__file__).resolve().parent
    client_config = json.loads((root / "resources/config.json").read_text())
    if args.scene_3d or args.mode == "server":
        client_config["3dActivated"] = "true"
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
            class Handler(BackendHandler):
                def do_GET(self):
                    parsed = urlsplit(self.path)
                    if parsed.path == "/resources/mock_match.json" and args.fixture:
                        body = args.fixture.read_bytes()
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                        return
                    if parsed.path == "/resources/config.json":
                        body = json.dumps(client_config).encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                        return
                    if parsed.path == "/__mock_trace":
                        event = parse_qs(parsed.query).get("event", [""])[0]
                        with (logs / "mock.log").open("a") as mock_log:
                            mock_log.write(event.replace("\n", " ").replace("\r", " ") + "\n")
                        self.send_response(204)
                        self.end_headers()
                        return
                    if getattr(self.server, "service", None) is not None:
                        super().do_GET()
                    else:
                        SimpleHTTPRequestHandler.do_GET(self)

                def log_message(self, fmt, *values):
                    http_log.write((fmt % values) + "\n")

            server = ThreadingHTTPServer(
                ("127.0.0.1", 0), partial(Handler, directory=str(root))
            )
            service = Service(args.database, config) if args.mode == "server" and not args.server_url else None
            server.service = service
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_address[1]
            tutorial = "1" if args.mode == "tutorial" else "0"
            mock = "1" if args.mode == "mock" else "0"
            from urllib.parse import urlencode
            parameters = {"lang": args.lang, "tuto": tutorial, "mock": mock,
                          "server": "1" if args.mode == "server" else "0"}
            if language_override:
                parameters["languageOverride"]="1"
            if args.profile:
                parameters["profile"] = args.profile
            if args.server_url:
                parameters["backend"] = args.server_url.rstrip("/")
            url = f"http://127.0.0.1:{port}/bin/boufbowl-client-1.9.6.swf?{urlencode(parameters)}"
            language_label=args.lang if language_override else "saved language or " + args.lang
            print(f"Starting Boufbowl {args.mode} ({language_label}). Logs: {logs}", flush=True)
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
                if service:
                    service.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except ServiceError as error:
        import sys
        print(f"Cannot start Boufbowl: {error}", file=sys.stderr)
        raise SystemExit(1)
