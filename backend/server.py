#!/usr/bin/env python3
"""Serve the original client assets and authenticated replacement backend."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit, unquote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.service import Service
from backend.storage import ServiceError
from tools.flash_protocol import ProtocolError
from tools.game_config import DEFAULT_CONFIG, ROOT, load_config


def default_database():
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "boufbowl-offline/backend.sqlite"


class Handler(SimpleHTTPRequestHandler):
    def json_response(self, response):
        payload = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        route = urlsplit(self.path).path
        routes = {"/api/hello": self.server.service.hello, "/api/command": self.server.service.command,
                  "/api/poll": self.server.service.poll, "/api/replay": self.replay}
        if route not in routes:
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1024 * 1024:
                raise ServiceError("BODY_SIZE", "Request body must be between 1 byte and 1 MiB")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ServiceError("BODY_INVALID", "Request body must be an object")
            response = routes[route](body)
        except ServiceError as error:
            response = {"ok": False, "code": error.code, "error": str(error),
                        "retryable": error.code in ("ENGINE_UNAVAILABLE", "ENGINE_TIMEOUT")}
        except (ProtocolError, ValueError, KeyError, TypeError) as error:
            response = {"ok": False, "code": "REQUEST_INVALID", "error": str(error)}
        self.json_response(response)

    def replay(self, body):
        from backend.replay import export_replay
        service = self.server.service
        with service.store.transaction():
            profile = service.store.authenticate(body.get("session"))
            return {"ok": True, "replay": export_replay(service, int(body["match"]), bool(body.get("verify")), profile)}

    def do_GET(self):
        route = urlsplit(self.path).path
        if route == "/api/health":
            self.json_response({"ok": True, "service": "boufbowl-offline", "protocol": "1.9.6", "schema_version": 1,
                                "rules_version": self.server.service.config["rules_version"]})
            return
        if route == "/crossdomain.xml":
            body = b'<cross-domain-policy><allow-access-from domain="*" secure="false"/><allow-http-request-headers-from domain="*" headers="Content-Type" secure="false"/></cross-domain-policy>'
            self.send_response(200)
            self.send_header("Content-Type", "application/xml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if not any(route.startswith(prefix) for prefix in ("/bin/", "/assets/", "/resources/")):
            self.send_error(404)
            return
        resolved = Path(self.translate_path(unquote(route))).resolve()
        allowed = [Path(self.directory).resolve() / name for name in ("bin", "assets", "resources")]
        if not any(resolved.is_relative_to(directory) for directory in allowed):
            self.send_error(404)
            return
        super().do_GET()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9900)
    parser.add_argument("--database", type=Path, default=default_database())
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    service = Service(args.database, load_config(args.config))
    server = ThreadingHTTPServer((args.host, args.port), partial(Handler, directory=str(ROOT)))
    server.service = service
    print(f"Boufbowl backend: http://{args.host}:{args.port}; database: {args.database}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        service.close()


if __name__ == "__main__":
    main()
