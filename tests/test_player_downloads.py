"""Player downloads must connect remotely and contain no local backend."""
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile
import shlex
from tools.build_player_downloads import build


class PlayerDownloadsTests(unittest.TestCase):
    def test_remote_launchers_bundle_only_player_and_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'bin').mkdir()
            (root / 'bin/flashplayer_32_sa.exe').write_bytes(b'player')
            (root / 'bin/boufbowl-client-1.9.6.swf').write_bytes(b'client')
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
