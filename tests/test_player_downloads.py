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
from unittest.mock import patch


class PlayerDownloadsTests(unittest.TestCase):
    @patch('tools.build_player_downloads.windows_executable', side_effect=lambda archive, *args: archive.with_suffix('.exe'))
    @patch('tools.build_player_downloads.desktop_client', side_effect=lambda root, *args, **kwargs: root/'bin/boufbowl-client-1.9.6.swf')
    def test_hosted_server_default_is_shared_and_required(self, compile_client, compile_wrapper):
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
            (root/'icons').mkdir()
            (root/'icons/icon-256.png').write_bytes(b'icon')
            with patch('tools.build_player_downloads.build_icons', return_value=root/'icons'):
                windows, linux = build(root)
            with zipfile.ZipFile(windows.with_suffix('.zip')) as archive:
                launcher = archive.read('Boufbowl/Jouer.cmd').decode()
                self.assertIn('bin\\boufbowl-client-1.9.6.swf', launcher)
                self.assertNotIn('https://', launcher)
                self.assertEqual(archive.read('Boufbowl/bin/boufbowl-client-1.9.6.swf'), b'client')
                self.assertEqual({name for name in archive.namelist() if name.lower().endswith('.cmd')}, {'Boufbowl/Jouer.cmd'})
                self.assertEqual(archive.read('Boufbowl/assets/sounds/kick.mp3'), b'audio')
                self.assertEqual(archive.read('Boufbowl/resources/config.json'), b'{}')
                self.assertNotIn('Boufbowl/assets/site/home.webp', archive.namelist())
            with tarfile.open(linux.with_suffix('.tar.gz')) as archive:
                self.assertIn('exec wine cmd /d /c Jouer.cmd', archive.extractfile('Boufbowl/jouer.sh').read().decode())
                self.assertEqual(archive.extractfile('Boufbowl/bin/boufbowl-client-1.9.6.swf').read(), b'client')
                self.assertEqual(archive.extractfile('Boufbowl/assets/sounds/kick.mp3').read(), b'audio')
                self.assertEqual(archive.extractfile('Boufbowl/resources/config.json').read(), b'{}')
                self.assertNotIn('Boufbowl/assets/site/home.webp', archive.getnames())

    @patch('tools.build_player_downloads.windows_executable', side_effect=lambda archive, *args: archive.with_suffix('.exe'))
    @patch('tools.build_player_downloads.desktop_client', side_effect=lambda root, *args, **kwargs: root/'bin/boufbowl-client-1.9.6.swf')
    def test_remote_player_packages_include_game_assets(self, compile_client, compile_wrapper):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'bin').mkdir()
            (root / 'bin/flashplayer_32_sa.exe').write_bytes(b'player')
            (root / 'bin/boufbowl-client-1.9.6.swf').write_bytes(b'client')
            (root / 'assets').mkdir()
            (root / 'resources').mkdir()
            (root/'icons').mkdir()
            (root/'icons/icon-256.png').write_bytes(b'icon')
            with patch('tools.build_player_downloads.build_icons', return_value=root/'icons'):
                windows, linux = build(root, 'https://game.example')
            with zipfile.ZipFile(windows.with_suffix('.zip')) as archive:
                self.assertEqual(set(archive.namelist()), {'Boufbowl/icon.png', 'Boufbowl/flashplayer.exe', 'Boufbowl/Jouer.cmd', 'Boufbowl/LIRE-MOI.txt', 'Boufbowl/bin/boufbowl-client-1.9.6.swf'})
                launcher = archive.read('Boufbowl/Jouer.cmd').decode()
                self.assertIn('bin\\boufbowl-client-1.9.6.swf', launcher)
                self.assertIn('FlashPlayerTrust', launcher)
                self.assertNotIn('https://', launcher)
                self.assertNotIn('wine', launcher)
                self.assertNotIn('python', launcher)
            with tarfile.open(linux.with_suffix('.tar.gz')) as archive:
                self.assertEqual(set(archive.getnames()), {'Boufbowl/icon.png', 'Boufbowl/flashplayer.exe', 'Boufbowl/Jouer.cmd', 'Boufbowl/jouer.sh', 'Boufbowl/LIRE-MOI.txt', 'Boufbowl/bin/boufbowl-client-1.9.6.swf'})
                launcher = archive.extractfile('Boufbowl/jouer.sh').read().decode()
                command = shlex.split(launcher.splitlines()[-1])
                self.assertEqual(command, ['exec', 'wine', 'cmd', '/d', '/c', 'Jouer.cmd'])
                self.assertIn('FlashPlayerTrust', archive.extractfile('Boufbowl/Jouer.cmd').read().decode())
                self.assertNotIn('python', launcher)
                self.assertEqual(archive.getmember('Boufbowl/jouer.sh').mode, 0o755)
            for url in ('http://game.example', 'https://user:pass@game.example', 'https://game.example?query=1'):
                with self.assertRaises(ValueError):
                    build(root, url)
