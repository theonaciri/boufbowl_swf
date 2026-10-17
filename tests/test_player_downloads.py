"""Player downloads must connect remotely and contain no local backend."""
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile
import shlex
import json
from tools.player_server import player_server
from tools.build_player_downloads import build


class PlayerDownloadsTests(unittest.TestCase):
    def test_hosted_server_default_is_shared_and_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, 'hosted server'):
                player_server(root)
            (root/'resources').mkdir(exist_ok=True)
            (root/'resources/site.json').write_text(json.dumps({'server_url':'https://hosted.example/'}))
            self.assertEqual(player_server(root), 'https://hosted.example')
            self.assertEqual(player_server(root, 'https://override.example'), 'https://override.example')
            (root/'bin').mkdir()
            (root/'bin/flashplayer_32_sa.exe').write_bytes(b'player')
            (root/'bin/boufbowl-client-1.9.6.swf').write_bytes(b'client')
            (root/'assets/sounds').mkdir(parents=True)
            (root/'assets/site').mkdir(parents=True)
            (root/'assets/sounds/kick.mp3').write_bytes(b'audio')
            (root/'assets/site/home.webp').write_bytes(b'web')
            (root/'resources/config.json').write_text('{}')
            windows, linux = build(root)
            with zipfile.ZipFile(windows) as archive:
                launcher = archive.read('Boufbowl/Jouer.cmd').decode()
                self.assertIn('https://hosted.example/bin/', launcher)
                self.assertEqual({name for name in archive.namelist() if name.lower().endswith('.cmd')}, {'Boufbowl/Jouer.cmd'})
                self.assertEqual(archive.read('Boufbowl/assets/sounds/kick.mp3'), b'audio')
                self.assertEqual(archive.read('Boufbowl/resources/config.json'), b'{}')
                self.assertNotIn('Boufbowl/assets/site/home.webp', archive.namelist())
            with tarfile.open(linux) as archive:
                self.assertIn('https://hosted.example/bin/', archive.extractfile('Boufbowl/jouer.sh').read().decode())
                self.assertEqual(archive.extractfile('Boufbowl/assets/sounds/kick.mp3').read(), b'audio')
                self.assertEqual(archive.extractfile('Boufbowl/resources/config.json').read(), b'{}')
                self.assertNotIn('Boufbowl/assets/site/home.webp', archive.getnames())

    def test_remote_player_packages_include_game_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'bin').mkdir()
            (root / 'bin/flashplayer_32_sa.exe').write_bytes(b'player')
            (root / 'bin/boufbowl-client-1.9.6.swf').write_bytes(b'client')
            (root / 'assets').mkdir()
            (root / 'resources').mkdir()
            windows, linux = build(root, 'https://game.example')
            with zipfile.ZipFile(windows) as archive:
                self.assertEqual(set(archive.namelist()), {'Boufbowl/flashplayer.exe', 'Boufbowl/Jouer.cmd', 'Boufbowl/LIRE-MOI.txt'})
                launcher = archive.read('Boufbowl/Jouer.cmd').decode()
                self.assertIn('https://game.example/bin/boufbowl-client-1.9.6.swf?', launcher)
                self.assertIn('backend=https%%3A%%2F%%2Fgame.example', launcher)
                self.assertIn('server=1', launcher)
                self.assertNotIn('wine', launcher)
                self.assertNotIn('python', launcher)
            with tarfile.open(linux) as archive:
                self.assertEqual(set(archive.getnames()), {'Boufbowl/flashplayer.exe', 'Boufbowl/jouer.sh', 'Boufbowl/LIRE-MOI.txt'})
                launcher = archive.extractfile('Boufbowl/jouer.sh').read().decode()
                command = shlex.split(launcher.splitlines()[-1])
                self.assertEqual(command[:3], ['exec', 'wine', './flashplayer.exe'])
                self.assertTrue(command[3].startswith('https://game.example/bin/'))
                self.assertIn('backend=https%3A%2F%2Fgame.example', command[3])
                self.assertNotIn('python', launcher)
                self.assertEqual(archive.getmember('Boufbowl/jouer.sh').mode, 0o755)
            for url in ('http://game.example', 'https://user:pass@game.example', 'https://game.example?query=1'):
                with self.assertRaises(ValueError):
                    build(root, url)
