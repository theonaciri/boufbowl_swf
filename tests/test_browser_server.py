from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import json
import hashlib
import tempfile
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from backend.server import Handler


class BrowserServerTests(unittest.TestCase):
    def test_browser_assets_and_static_file_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vendor/ruffle").mkdir(parents=True)
            (root / "bin").mkdir()
            client = root / "bin/boufbowl-client-1.9.6.swf"
            client.write_bytes(b"first client")
            (root / "resources").mkdir()
            (root / "resources/config.json").write_text('{"3dActivated":"false","sound":{"enabled":"true"}}')
            (root / "browser.html").write_text("browser")
            (root / "vendor/ruffle/ruffle.js").write_text("player")
            (root / "vendor/ruffle/player.wasm").write_bytes(b"\0asm")
            (root / "private.txt").write_text("private")
            (root / "vendor/ruffle/escape.txt").symlink_to(root / "private.txt")

            class QuietHandler(Handler):
                def log_message(self, *args):
                    pass

            server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=directory))
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                origin = f"http://127.0.0.1:{server.server_port}"
                for payload in (b"first client", b"updated client"):
                    client.write_bytes(payload)
                    with urlopen(origin + "/api/client") as response:
                        manifest = json.load(response)
                        self.assertTrue(manifest["url"].endswith(hashlib.sha256(payload).hexdigest()))
                        self.assertEqual(response.headers["Cache-Control"], "no-store")
                    with urlopen(origin + manifest["url"]) as response:
                        self.assertEqual(response.read(), payload)
                with urlopen(origin + "/resources/config.json") as response:
                    config = json.load(response)
                    self.assertEqual(config["3dActivated"], "true")
                    self.assertEqual(config["sound"], {"enabled": "true"})
                    self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertEqual(json.loads((root / "resources/config.json").read_text())["3dActivated"], "false")
                for method in ("GET", "HEAD"):
                    for route in ("/", "/browser.html", "/vendor/ruffle/ruffle.js", "/vendor/ruffle/player.wasm"):
                        with self.subTest(method=method, route=route):
                            with urlopen(Request(origin + route, method=method)) as response:
                                self.assertEqual(response.status, 200)
                                if route.endswith(".wasm"):
                                    self.assertEqual(response.headers.get_content_type(), "application/wasm")
                    for route in ("/private.txt", "/vendor/ruffle/../../private.txt", "/vendor/ruffle/escape.txt", "/bin/%2e%2e/private.txt"):
                        with self.subTest(method=method, route=route):
                            with self.assertRaises(HTTPError) as error:
                                urlopen(Request(origin + route, method=method))
                            self.assertEqual(error.exception.code, 404)
                            error.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
