#!/usr/bin/env python3
"""Serve the original client assets and authenticated replacement backend."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import hashlib
import os
import ssl
import ipaddress
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


class BackendHTTPServer(ThreadingHTTPServer):
    # Reconnects after a mobile network recovers can arrive in a burst.
    request_queue_size = 1024


class Handler(SimpleHTTPRequestHandler):
    def json_response(self, response):
        payload = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError,ConnectionResetError):
            pass  # A client can cancel its request before the response is ready.

    def do_POST(self):
        route = urlsplit(self.path).path
        routes = {"/api/hello": self.server.service.hello, "/api/command": self.server.service.command,
                  "/api/poll": self.server.service.poll, "/api/replay": self.replay,
                  "/api/community": self.server.service.community,
                  "/api/account": lambda body: self.server.service.account(body, self.client_address[0])}
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
            if route == '/api/account' and body.get('action') != 'logout' and not isinstance(self.connection,ssl.SSLSocket) and not ipaddress.ip_address(self.client_address[0]).is_loopback:
                raise ServiceError('ACCOUNT_TLS','Remote password authentication requires an HTTPS server')
            response = routes[route](body)
        except ServiceError as error:
            response = {"ok": False, "code": error.code, "error": str(error),
                        "retryable": error.code in ("ENGINE_UNAVAILABLE", "ENGINE_TIMEOUT", "SERVICE_STOPPING")}
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
        if route == "/api/client":
            client = Path(self.directory) / "bin/boufbowl-client-1.9.6.swf"
            digest = hashlib.sha256(client.read_bytes()).hexdigest()
            self.json_response({"url": "/bin/boufbowl-client-1.9.6.swf?v=" + digest})
            return
        if route == "/__mock_trace":
            # The shipped client emits optional launcher diagnostics here.
            self.send_response(204)
            self.end_headers()
            return
        if route == "/resources/config.json":
            # Standalone server clients need the same resolution scene override
            # as play.py's server mode. The on-disk default is for menu mode.
            config = json.loads((Path(self.directory) / "resources/config.json").read_text())
            config["3dActivated"] = "true"
            self.json_response(config)
            return
        if route == "/api/health":
            self.json_response({"ok": True, "service": "boufbowl-offline", "protocol": "1.9.6", "schema_version": 8,
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
        super().do_GET()

    def send_head(self):
        # Apply the static-file allowlist to both GET and HEAD requests.
        route = urlsplit(self.path).path
        if route == "/":
            self.path = "/browser.html"
            route = "/browser.html"
        if route != "/browser.html" and not any(route.startswith(prefix) for prefix in ("/bin/", "/assets/", "/resources/", "/vendor/ruffle/")):
            self.send_error(404)
            return
        resolved = Path(self.translate_path(unquote(route))).resolve()
        root = Path(self.directory).resolve()
        allowed = [root / name for name in ("bin", "assets", "resources", "vendor/ruffle")]
        if resolved != root / "browser.html" and not any(resolved.is_relative_to(directory) for directory in allowed):
            self.send_error(404)
            return
        return super().send_head()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9900)
    parser.add_argument("--database", type=Path, default=default_database())
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--tls-cert", type=Path)
    parser.add_argument("--tls-key", type=Path)
    args = parser.parse_args()
    if bool(args.tls_cert) != bool(args.tls_key):
        parser.error("Provide both --tls-cert and --tls-key")
    service = Service(args.database, load_config(args.config))
    server = BackendHTTPServer((args.host, args.port), partial(Handler, directory=str(ROOT)))
    server.service = service
    if args.tls_cert:
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(args.tls_cert,args.tls_key)
        server.socket=context.wrap_socket(server.socket,server_side=True)
    scheme='https' if args.tls_cert else 'http'
    print(f"Boufbowl backend: {scheme}://{args.host}:{args.port}; database: {args.database}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        service.stop()
        server.server_close()
        service.close()


if __name__ == "__main__":
    main()
