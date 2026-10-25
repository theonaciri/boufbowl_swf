"""Player downloads must connect remotely and contain no local backend."""
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile
import shlex
import json
from tools.player_server import player_server
from tools.build_player_downloads import build as original_build
from unittest.mock import patch


def build(root,*args,**kwargs):
    (root/'resources').mkdir(exist_ok=True)
    (root/'resources/release.json').write_text(json.dumps({'version':'0.1.0','android_build':1000001}))
    def updaters(root,platforms):
        result={}
        for platform in platforms:
            file=root/('updater-'+platform);file.write_bytes(b'updater');file.chmod(0o755);result[platform]=file
        return result
    with patch('tools.build_player_downloads.build_updaters',side_effect=updaters):
        return original_build(root,*args,**kwargs)


def fake_executable(archive, *args):
    output = archive.with_suffix('.exe')
    output.write_bytes(b'executable')
    return output


class PlayerDownloadsTests(unittest.TestCase):
    @patch('tools.build_player_downloads.windows_executable', side_effect=fake_executable)
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
            (root/'icons/icon.ico').write_bytes(b'ico')
            (root/'makensis').write_bytes(b'compiler')
            with patch('tools.build_player_downloads.build_icons', return_value=root/'icons'):
                windows, linux = build(root, makensis=root/'makensis')
            with zipfile.ZipFile(windows.with_suffix('.zip')) as archive:
                launcher = archive.read('Boufbowl/Jouer-game.cmd').decode()
                self.assertIn('bin\\boufbowl-client-1.9.6.swf', launcher)
                self.assertNotIn('https://', launcher)
                self.assertEqual(archive.read('Boufbowl/bin/boufbowl-client-1.9.6.swf'), b'client')
                self.assertEqual({name for name in archive.namelist() if name.lower().endswith('.cmd')}, {'Boufbowl/Jouer.cmd','Boufbowl/Jouer-game.cmd'})
                self.assertEqual(archive.read('Boufbowl/assets/sounds/kick.mp3'), b'audio')
                self.assertEqual(archive.read('Boufbowl/resources/config.json'), b'{}')
                self.assertNotIn('Boufbowl/assets/site/home.webp', archive.namelist())
            with tarfile.open(linux.with_suffix('.tar.gz')) as archive:
                self.assertIn('exec wine cmd /d /c Jouer-game.cmd', archive.extractfile('Boufbowl/jouer-game.sh').read().decode())
                self.assertEqual(archive.extractfile('Boufbowl/bin/boufbowl-client-1.9.6.swf').read(), b'client')
                self.assertEqual(archive.extractfile('Boufbowl/assets/sounds/kick.mp3').read(), b'audio')
                self.assertEqual(archive.extractfile('Boufbowl/resources/config.json').read(), b'{}')
                self.assertNotIn('Boufbowl/assets/site/home.webp', archive.getnames())

    @patch('tools.build_player_downloads.windows_executable', side_effect=fake_executable)
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
            (root/'icons/icon.ico').write_bytes(b'ico')
            (root/'makensis').write_bytes(b'compiler')
            with patch('tools.build_player_downloads.build_icons', return_value=root/'icons'):
                windows, linux = build(root, 'https://game.example', makensis=root/'makensis')
                first_mtimes = [path.stat().st_mtime_ns for path in (windows, linux)]
                again = build(root, 'https://game.example', makensis=root/'makensis')
                self.assertEqual(first_mtimes, [path.stat().st_mtime_ns for path in again])
                self.assertEqual(compile_wrapper.call_count, 1)
                (root/'assets/change.bin').write_bytes(b'new asset')
                build(root, 'https://game.example', makensis=root/'makensis')
                self.assertEqual(compile_wrapper.call_count, 2)
                (root/'assets/change.bin').unlink()
                build(root, 'https://game.example', makensis=root/'makensis')
            with zipfile.ZipFile(windows.with_suffix('.zip')) as archive:
                self.assertEqual(set(archive.namelist()), {'Boufbowl/icon.png', 'Boufbowl/flashplayer.exe', 'Boufbowl/Jouer.cmd','Boufbowl/Jouer-game.cmd','Boufbowl/BoufbowlUpdater.exe','Boufbowl/update-client.json','Boufbowl/resources/release.json', 'Boufbowl/LIRE-MOI.txt', 'Boufbowl/bin/boufbowl-client-1.9.6.swf'})
                launcher = archive.read('Boufbowl/Jouer-game.cmd').decode()
                self.assertIn('bin\\boufbowl-client-1.9.6.swf', launcher)
                self.assertIn('FlashPlayerTrust', launcher)
                self.assertNotIn('https://', launcher)
                self.assertNotIn('wine', launcher)
                self.assertNotIn('python', launcher)
            with tarfile.open(linux.with_suffix('.tar.gz')) as archive:
                self.assertEqual(set(archive.getnames()), {'Boufbowl/icon.png', 'Boufbowl/flashplayer.exe','Boufbowl/Jouer-game.cmd','Boufbowl/BoufbowlUpdater','Boufbowl/update-client.json','Boufbowl/resources/release.json', 'Boufbowl/jouer.sh','Boufbowl/jouer-game.sh', 'Boufbowl/LIRE-MOI.txt', 'Boufbowl/bin/boufbowl-client-1.9.6.swf'})
                launcher = archive.extractfile('Boufbowl/jouer.sh').read().decode()
                command = shlex.split(launcher.splitlines()[-1])
                self.assertEqual(command, ['exec', './BoufbowlUpdater'])
                self.assertIn('FlashPlayerTrust', archive.extractfile('Boufbowl/Jouer-game.cmd').read().decode())
                self.assertNotIn('python', launcher)
                self.assertEqual(archive.getmember('Boufbowl/jouer.sh').mode, 0o755)
            for url in ('http://game.example', 'https://user:pass@game.example', 'https://game.example?query=1'):
                with self.assertRaises(ValueError):
                    build(root, url)


    @patch('tools.build_player_downloads.windows_executable', side_effect=fake_executable)
    @patch('tools.build_player_downloads.desktop_client', side_effect=lambda root, *args, **kwargs: root/'bin/boufbowl-client-1.9.6.swf')
    def test_tool_changes_exclusions_and_missing_outputs_invalidate_only_affected_packages(self, compile_client, compile_wrapper):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ('bin', 'resources', 'assets/site', 'assets/textures/stadiums', 'icons'):
                (root/folder).mkdir(parents=True, exist_ok=True)
            for name, data in {'bin/flashplayer_32_sa.exe': b'player', 'bin/boufbowl-client-1.9.6.swf': b'client',
                               'icons/icon-256.png': b'icon', 'icons/icon.ico': b'ico', 'makensis': b'compiler'}.items():
                (root/name).write_bytes(data)
            with patch('tools.build_player_downloads.build_icons', return_value=root/'icons'):
                def package(platforms=None):
                    return build(root, 'https://game.example', makensis=root/'makensis', platforms=platforms)
                windows, linux = package()
                original_linux = linux.stat().st_mtime_ns
                (root/'assets/site/website-only.webp').write_bytes(b'website')
                (root/'assets/textures/stadiums/grass.avif').write_bytes(b'website preview')
                package()
                self.assertEqual(compile_wrapper.call_count, 1)
                self.assertEqual(linux.stat().st_mtime_ns, original_linux)
                (root/'makensis').write_bytes(b'new compiler')
                package()
                self.assertEqual(compile_wrapper.call_count, 2)
                self.assertEqual(linux.stat().st_mtime_ns, original_linux)
                windows.unlink()
                package()
                self.assertEqual(compile_wrapper.call_count, 3)
                self.assertEqual(linux.stat().st_mtime_ns, original_linux)
                linux.write_bytes(b'corrupt')
                package(['linux'])
                self.assertEqual(compile_wrapper.call_count, 3)
                self.assertTrue(linux.read_bytes().startswith(b'#!/bin/sh'))
