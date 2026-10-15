import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

import play
from tools.build_mock_fixture import build_fixture


class LauncherTests(unittest.TestCase):
    def test_server_launch_passes_its_live_backend_and_current_client_revision(self):
        # Exercise the real launcher HTTP service without starting Wine or
        # touching the user's Flash preferences. Explicit backend overrides any
        # stale BoufbowlConnection address saved by the native client.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(__file__).resolve().parent.parent
            arguments = ['play.py', '--mode', 'server', '--profile', 'Launcher Check',
                         '--database', str(Path(directory) / 'state.sqlite')]

            def launch(command, **kwargs):
                query = parse_qs(urlsplit(command[-1]).query)
                self.assertEqual(query['server'], ['1'])
                self.assertEqual(query['v'], [hashlib.sha256((root / 'bin/boufbowl-client-1.9.6.swf').read_bytes()).hexdigest()])
                origin = query['backend'][0]
                parsed = urlsplit(command[-1])
                self.assertEqual(origin, f'{parsed.scheme}://{parsed.netloc}')
                roster = build_fixture()['steps'][0]['decoded']['leftRoster']
                club = {'clubId': '1', 'clubName': 'Launch Club', 'boufbowler': roster['characters'],
                        'paletteId': 1, 'firstColor': roster['firstColor'], 'secondColor': roster['secondColor'],
                        'patternColor': roster['patternColor'], 'sigilBackground': 1, 'sigilCharge': 1,
                        'isPredefinedClub': False}
                body = json.dumps({'nickname': 'Launcher Check', 'clubs': [club]}).encode()
                with urlopen(Request(origin + '/api/hello', data=body,
                                     headers={'Content-Type': 'application/json'})) as response:
                    self.assertTrue(json.load(response)['ok'])
                return 0

            real_which = play.shutil.which
            with patch.dict(os.environ, {'XDG_DATA_HOME': directory, 'XDG_STATE_HOME': directory}), \
                 patch('sys.argv', arguments), patch.object(play.shutil, 'which', side_effect=lambda name: '/usr/bin/wine' if name == 'wine' else real_which(name)), \
                 patch.object(play.subprocess, 'run'), patch.object(play.subprocess, 'call', side_effect=launch) as wine:
                self.assertEqual(play.main(), 0)
                wine.assert_called_once()
