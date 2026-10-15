"""Homepage routes, legacy game links and safe build discovery."""
from functools import partial
from pathlib import Path
import json
import tempfile
from threading import Thread
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import unittest
from backend.server import Handler, STATIC_PAGES, site_manifest


class HomepageTests(unittest.TestCase):
    def test_manifest_only_advertises_existing_builds_or_safe_external_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.assertIsNone(site_manifest(root)['downloads']['android']['url'])
            (root/'android/build').mkdir(parents=True)
            (root/'android/build/BoufbowlOffline.apk').write_bytes(b'apk')
            data=site_manifest(root)
            self.assertEqual(data['downloads']['android']['url'],'/downloads/BoufbowlOffline.apk')
            self.assertEqual(data['downloads']['android']['size'],3)
            (root/'windows/build').mkdir(parents=True)
            (root/'windows/build/Boufbowl-windows.zip').write_bytes(b'windows')
            data=site_manifest(root)
            self.assertEqual(data['downloads']['windows']['url'],'/downloads/Boufbowl-windows.zip')
            self.assertEqual(data['downloads']['windows']['size'],7)
            self.assertEqual(data['downloads']['windows']['description'],'Windows · sans Wine ni Python')
            (root/'resources').mkdir()
            (root/'resources/site.json').write_text(json.dumps({'contact_url':'javascript:alert(1)',
                'desktop_download_url':'https://example.com/game.tar.gz'}))
            data=site_manifest(root)
            self.assertIsNone(data['contact_url'])
            self.assertEqual(data['downloads']['desktop']['url'],'https://example.com/game.tar.gz')
            self.assertFalse(data['downloads']['desktop']['local'])
            (root/'resources/site.json').write_text('[]')
            self.assertTrue(site_manifest(root)['ok'])

    def test_home_game_redirect_and_download_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in STATIC_PAGES: (root/name).write_text(name)
            (root/'android/build').mkdir(parents=True)
            (root/'android/build/BoufbowlOffline.apk').write_bytes(b'build')
            (root/'windows/build').mkdir(parents=True)
            (root/'windows/build/Boufbowl-windows.zip').write_bytes(b'windows')
            (root/'private.txt').write_text('secret')
            class QuietHandler(Handler):
                def log_message(self,*args):pass
            server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=directory))
            thread=Thread(target=server.serve_forever,daemon=True);thread.start()
            origin='http://127.0.0.1:'+str(server.server_port)
            try:
                for method in ('GET','HEAD'):
                    with urlopen(Request(origin+'/',method=method)) as response:
                        self.assertEqual(response.status,200)
                        if method=='GET':self.assertEqual(response.read(),b'index.html')
                    with urlopen(Request(origin+'/browser.html',method=method)) as response:
                        self.assertTrue(response.url.endswith('/play.html'))
                    with urlopen(Request(origin+'/downloads/BoufbowlOffline.apk',method=method)) as response:
                        self.assertEqual(response.status,200)
                        if method=='GET':self.assertEqual(response.read(),b'build')
                    with urlopen(Request(origin+'/downloads/Boufbowl-windows.zip',method=method)) as response:
                        self.assertEqual(response.headers['Content-Length'],'7')
                        if method=='GET':self.assertEqual(response.read(),b'windows')
                with urlopen(origin+'/api/site') as response:self.assertTrue(json.load(response)['ok'])
                for route in ('/downloads/private.txt','/downloads/../private.txt','/android/build/BoufbowlOffline.apk'):
                    with self.assertRaises(HTTPError) as error:urlopen(origin+route)
                    error.exception.close()
                (root/'android/build/BoufbowlOffline.apk').unlink()
                (root/'android/build/BoufbowlOffline.apk').symlink_to(root/'private.txt')
                self.assertIsNone(site_manifest(root)['downloads']['android']['url'])
                with self.assertRaises(HTTPError) as error:urlopen(origin+'/downloads/BoufbowlOffline.apk')
                error.exception.close()
            finally:
                server.shutdown();server.server_close();thread.join(timeout=5)

    def test_android_remote_server_is_injected_without_changing_configuration(self):
        from tools.game_config import startup_source, load_config, ROOT
        config=load_config()
        source=(ROOT/'android/patches/StartUpApplicationCommand.as').read_text()
        result=startup_source(source,config,android=True,server_url='https://example.com')
        self.assertIn('if(url == null || url == "") url = "https://example.com";',result)
        self.assertEqual(config['general']['server']['host'],'127.0.0.1')
