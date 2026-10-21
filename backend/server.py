#!/usr/bin/env python3
"""Serve the original client assets and authenticated replacement backend."""
import argparse
from functools import partial, lru_cache
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import hashlib
import os
import ssl
import ipaddress
import time
import queue
import traceback
from pathlib import Path
import sys
from urllib.parse import urlsplit, unquote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.service import Service
from backend.storage import ServiceError
from backend.asset_contributions import AssetContributions
from tools.flash_protocol import ProtocolError
from tools.game_config import DEFAULT_CONFIG, ROOT, load_config


def default_database():
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "boufbowl-offline/backend.sqlite"


class BackendHTTPServer(ThreadingHTTPServer):
    # Reconnects after a mobile network recovers can arrive in a burst.
    request_queue_size = 1024


STATIC_PAGES = ("index.html", "play.html", "home.js", "site-activity.js", "restoration.js", "browser.html", "admin.html", "website-activity.html", "website-activity.js", "moderation.html", "tournaments.html",
                "admin.js", "moderation.js", "tournaments.js", "assets-admin.html", "assets-admin.js",
                "legal.html", "confidentialite.html", "conditions-utilisation.html",
                "mentions-legales.html", "cookies.html", "charte-communaute.html", "reglement-tournois.html")


DOWNLOAD_FILES = {
    '/downloads/BoufbowlOffline.apk': ('android/build/BoufbowlOffline.apk', 'android'),
    '/downloads/Boufbowl-linux.run': ('linux/build/Boufbowl-linux.run', 'desktop'),
    '/downloads/Boufbowl-windows.exe': ('windows/build/Boufbowl-windows.exe', 'windows'),
}


def download_path(root, relative):
    path = root / relative
    # Only known build artifacts may be served; symlinks cannot escape their build folder.
    return path if path.is_file() and path.resolve().is_relative_to(root / Path(relative).parent) else None


@lru_cache(maxsize=12)
def download_revision(filename, modified_ns, size, inode):
    # The stat fields invalidate the cache when a bundle is replaced atomically.
    digest = hashlib.sha256()
    with open(filename, 'rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()[:16]


def site_manifest(root):
    try:
        settings = json.loads((root / 'resources/site.json').read_text())
        if not isinstance(settings, dict): settings = {}
    except (OSError, ValueError):
        settings = {}

    def public_url(key):
        value = settings.get(key)
        if not isinstance(value, str): return None
        parsed = urlsplit(value)
        return value if parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password else None

    downloads = {}
    for route, (relative, platform) in DOWNLOAD_FILES.items():
        path = download_path(root, relative)
        external = public_url(platform + '_download_url')
        stat = path.stat() if path and not external else None
        revision = download_revision(str(path.resolve()), stat.st_mtime_ns, stat.st_size, stat.st_ino) if stat else None
        downloads[platform] = {
            'url': external or (route + '?v=' + revision if revision else None),
            'local': bool(path and not external),
            'size': stat.st_size if stat else None,
            'description': ('APK · Android 6+ · ARM64' if platform == 'android' else
                            'Windows' if platform == 'windows' else
                            'Desktop · client Flash' if external else 'Linux x86-64'),
        }
    return {'ok': True, 'downloads': downloads, 'contact_url': public_url('contact_url'),
            'tot_quote_source_url': public_url('tot_quote_source_url')}


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        cache_control = getattr(self, "_static_cache_control", None)
        if cache_control:
            self.send_header("Cache-Control", cache_control)
            self._static_cache_control = None
        super().end_headers()

    def json_response(self, response):
        if response.get('ok') is False:
            self._tracking_error = response.get('code', 'REQUEST_ERROR')
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

    def send_response(self, code, message=None):
        self._tracking_status = code
        super().send_response(code, message)

    def measured(self, method, handler):
        started = time.perf_counter()
        self._tracking_status = 500
        self._tracking_error = None
        self._tracking_detail = None
        request_path = urlsplit(self.path).path
        route = request_path
        if route.startswith('/assets/'):
            route = '/assets/*'
        elif route.startswith('/vendor/'):
            route = '/vendor/*'
        elif route.startswith('/bin/'):
            route = '/bin/*'
        elif route.startswith('/resources/'):
            route = '/resources/*'
        elif route.lstrip('/') not in STATIC_PAGES and route not in ('/', '/__mock_trace', '/crossdomain.xml',
                            '/api/hello', '/api/command', '/api/poll', '/api/replay', '/api/community',
                            '/api/account', '/api/telemetry', '/api/metrics', '/api/admin', '/api/site', '/api/client',
                            '/api/health', '/api/site-events', '/api/presence-counts'):
            route = '/unknown'
        try:
            handler()
        except Exception as error:
            self._tracking_error = 'INTERNAL_ERROR'
            self._tracking_detail = (str(error), traceback.format_exc())
            raise
        finally:
            service = getattr(self.server, 'service', None)
            tracker = getattr(service, 'tracking', None)
            if tracker is not None:
                failed = self._tracking_status >= 400 or self._tracking_error is not None
                tracker.observe('http', method + ' ' + route, (time.perf_counter() - started) * 1000, failed)
                if method == 'GET' and request_path.startswith('/assets/') and not failed:
                    tracker.website_asset_request(unquote(request_path))
                if failed:
                    message, stack = self._tracking_detail or (method + ' ' + route, '')
                    tracker.error('server', self._tracking_error or 'HTTP_' + str(self._tracking_status), message, stack)

    def do_POST(self):
        self.measured('POST', self.handle_post)

    def handle_post(self):
        route = urlsplit(self.path).path
        if route in ('/api/asset-token','/api/asset-upload','/api/asset-preview','/api/asset-download'):
            return self.asset_post(route)
        routes = {"/api/hello": self.server.service.hello, "/api/command": self.server.service.command,
                  "/api/poll": self.server.service.poll, "/api/replay": self.replay,
                  "/api/community": self.server.service.community,
                  "/api/metrics": self.server.service.metrics,
                  "/api/admin": self.server.service.admin,
                  "/api/telemetry": self.server.service.telemetry,
                  "/api/site-events": self.server.service.website_events,
                  "/api/presence-counts": self.server.service.live_presence,
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

    def asset_post(self,route):
        manager=getattr(self.server.service,'asset_contributions',None)
        identity=None
        try:
            if not manager:raise ServiceError('ASSET_UNAVAILABLE','Contributions indisponibles.')
            if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length',[]))!=1:
                raise ServiceError('BODY_SIZE','Longueur fixe unique obligatoire.')
            origin=self.headers.get('Origin')
            if origin:
                parsed=urlsplit(origin)
                if parsed.netloc!=self.headers.get('Host') or parsed.scheme not in ('http','https'):
                    raise ServiceError('ASSET_ORIGIN','Origine non autorisée.')
            if self.headers.get('X-Requested-With')!='BoufbowlAssets':
                raise ServiceError('ASSET_ORIGIN','En-tête de contribution obligatoire.')
            length=int(self.headers['Content-Length'])
            ip=self.client_address[0]
            if os.environ.get('BOUFBOWL_TRUST_CF')=='1' and ipaddress.ip_address(ip).is_loopback:
                forwarded=self.headers.get('CF-Connecting-IP')
                if forwarded:ip=str(ipaddress.ip_address(forwarded))
            if route=='/api/asset-upload':
                identity,path=manager.reserve(self.headers.get('X-Asset-Id'),self.headers.get('X-Asset-Token'),self.headers.get('X-Asset-Name',''),length,ip)
                remaining=length;started=time.monotonic();self.connection.settimeout(10)
                with path.open('xb') as output:
                    while remaining:
                        if time.monotonic()-started>120:raise ServiceError('ASSET_TIMEOUT','Envoi trop lent.')
                        chunk=self.rfile.read1(min(65536,remaining))
                        if not chunk:raise ServiceError('ASSET_INCOMPLETE','Envoi incomplet.')
                        output.write(chunk);remaining-=len(chunk)
                manager.finish(identity,path)
                self.json_response({'ok':True,'id':identity,'state':'queued','message':'Fichier reçu en quarantaine. Aucun remplacement automatique.'})
                return
            if not 0<length<=8192:raise ServiceError('BODY_SIZE','Requête trop grande.')
            self.connection.settimeout(10)
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict):raise ServiceError('ASSET_INVALID','Objet attendu.')
            if route=='/api/asset-token':
                self.json_response(manager.token(body.get('asset'),ip,body.get('consent'),body.get('contact')));return
            with self.server.service.store.transaction():
                actor=self.server.service.store.authenticate(body.get('session'))
                if self.server.service.role(actor)!='admin':raise ServiceError('ADMIN_FORBIDDEN','Administrateur requis.')
            data,mime=(manager.preview(body.get('id'),body.get('index',0)) if route=='/api/asset-preview' else manager.original(body.get('id')))
            self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"sandbox; default-src 'none'")
            if route=='/api/asset-download':self.send_header('Content-Disposition','attachment; filename="asset.bin"')
            self.end_headers();self.wfile.write(data)
        except (ServiceError,ValueError,OSError,TimeoutError,queue.Full) as error:
            if identity:manager.abort(identity)
            code=getattr(error,'code','ASSET_INVALID')
            payload=json.dumps({'ok':False,'code':code,'error':str(error)}).encode()
            self.send_response(429 if code=='ASSET_LIMIT' else 403 if code in ('ADMIN_FORBIDDEN','ASSET_ORIGIN','ASSET_TOKEN') else 400)
            self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(payload)))
            self.end_headers();self.wfile.write(payload)

    def replay(self, body):
        from backend.replay import export_replay
        service = self.server.service
        with service.store.transaction():
            profile = service.store.authenticate(body.get("session"))
            return {"ok": True, "replay": export_replay(service, int(body["match"]), bool(body.get("verify")), profile)}

    def do_GET(self):
        self.measured('GET', self.handle_get)

    def do_HEAD(self):
        self.measured('HEAD', super().do_HEAD)

    def handle_get(self):
        route = urlsplit(self.path).path
        if route == '/api/asset-catalog':
            from backend.asset_contributions import catalog
            self.json_response({'ok':True,'assets':list(catalog(Path(self.directory)).values())})
            return
        if route == "/api/site":
            self.json_response(site_manifest(Path(self.directory).resolve()))
            return
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
        # Static resources are safe to retain for a month. HTML is revalidated
        # so deploys can switch visitors to the current asset versions.
        self._static_cache_control = None
        if route == "/":
            self.path = "/index.html"
            route = "/index.html"
        if route == "/browser.html":
            self.send_response(302)
            self.send_header('Location', '/play.html')
            self.end_headers()
            return None
        if route in ("/website-tracking.html", "/website-analytics.html"):
            self.send_response(308)
            self.send_header('Location', '/website-activity.html')
            self.end_headers()
            return None
        legacy_downloads = {
            '/downloads/Boufbowl-windows.zip': '/downloads/Boufbowl-windows.exe',
            '/downloads/Boufbowl-linux.tar.gz': '/downloads/Boufbowl-linux.run',
        }
        if route in legacy_downloads:
            self.send_response(302)
            self.send_header('Location', legacy_downloads[route])
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            return None
        if route in DOWNLOAD_FILES:
            path = download_path(Path(self.directory).resolve(), DOWNLOAD_FILES[route][0])
            if path is None:
                self.send_error(404)
                return None
            self._static_cache_control = "public, max-age=2592000"
            self.path = '/' + DOWNLOAD_FILES[route][0]
            return super().send_head()
        if route.lstrip("/") not in STATIC_PAGES and not any(route.startswith(prefix) for prefix in ("/bin/", "/assets/", "/resources/", "/vendor/ruffle/")):
            self.send_error(404)
            return
        resolved = Path(self.translate_path(unquote(route))).resolve()
        root = Path(self.directory).resolve()
        allowed = [root / name for name in ("bin", "assets", "resources", "vendor/ruffle")]
        if resolved not in tuple(root / name for name in STATIC_PAGES) and not any(resolved.is_relative_to(directory) for directory in allowed):
            self.send_error(404)
            return
        if not resolved.is_file():
            self.send_error(404)
            return
        if route.endswith(".html") or route == "/":
            self._static_cache_control = "no-cache"
        else:
            self._static_cache_control = "public, max-age=2592000"
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
    service.asset_contributions=AssetContributions(ROOT,args.database.parent/"asset-contributions")
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
        service.asset_contributions.close()
        service.stop()
        server.server_close()
        service.close()


if __name__ == "__main__":
    main()
