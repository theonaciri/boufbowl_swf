"""Platform selection must avoid unrelated dependencies and keep secrets off argv."""
from contextlib import ExitStack, nullcontext
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from tools import build_players
from tools.media_fingerprints import file_hash, logic_fingerprint


class BuildPlayersTests(unittest.TestCase):
    def run_platform(self, selection, fresh=False):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        if 'linux' in selection or 'windows' in selection:
            (root/'bin').mkdir()
            (root/'bin/flashplayer_32_sa.exe').write_bytes(b'player')
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(build_players, 'ROOT', root))
        stack.enter_context(patch.object(build_players, 'game_rebuild_required', return_value=not fresh))
        stack.enter_context(patch('sys.argv', ['build_players', '--no-website', '--platform', *selection]))
        mocks = {}
        for name in ('air_sdk', 'android_sdk', 'jdk_directory', 'java_binary', 'ffdec_jar'):
            mocks[name] = stack.enter_context(patch.object(build_players, name, return_value=root/name))
        mocks['signing'] = stack.enter_context(patch.object(build_players, 'signing_credentials', return_value=(root/'cert', 'test-secret')))
        mocks['remember'] = stack.enter_context(patch.object(build_players, 'remember_build_tools'))
        mocks['which'] = stack.enter_context(patch.object(build_players.shutil, 'which', side_effect=lambda name: '/tools/'+str(name)))
        stack.enter_context(patch.object(build_players, 'build_budget', return_value=nullcontext()))
        mocks['run'] = stack.enter_context(patch.object(subprocess, 'run', return_value=SimpleNamespace(returncode=0)))
        build_players.main()
        return mocks

    def test_linux_does_not_discover_android_or_nsis(self):
        mocks = self.run_platform(['linux'])
        for name in ('air_sdk', 'android_sdk', 'jdk_directory', 'signing'):
            mocks[name].assert_not_called()
        self.assertNotIn('makensis', [call.args[0] for call in mocks['which'].call_args_list])
        command = mocks['run'].call_args_list[-1].args[0]
        self.assertIn('linux', command)
        self.assertNotIn('windows', command)
        self.assertIn('--rebuild-game', mocks['run'].call_args_list[0].args[0])

    def test_current_game_preserves_incremental_packaging(self):
        mocks = self.run_platform(['linux'], fresh=True)
        self.assertNotIn('--rebuild-game', mocks['run'].call_args_list[0].args[0])

    def test_rebuild_detection_checks_sources_and_output_not_just_swf_existence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, content in {
                'bin/base/boufbowl-client-1.9.6.swf': b'preserved',
                'bin/boufbowl-client-1.9.6.swf': b'compiled',
                'resources/game_config.json': b'{}',
                'patches/ClientRuntime.as.inc': b'policy',
            }.items():
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            receipt = root/'.local/game-build.json'
            receipt.parent.mkdir()
            self.assertTrue(build_players.game_rebuild_required(root))
            current = json.dumps({'client': file_hash(root/build_players.CLIENT),
                                  'logic': logic_fingerprint(root)})
            receipt.write_text(current)
            self.assertFalse(build_players.game_rebuild_required(root))
            policy = root/'patches/ClientRuntime.as.inc'
            policy.write_bytes(b'new policy')
            self.assertTrue(build_players.game_rebuild_required(root))
            policy.write_bytes(b'policy')
            self.assertFalse(build_players.game_rebuild_required(root))
            (root/build_players.CLIENT).write_bytes(b'other compiled client')
            self.assertTrue(build_players.game_rebuild_required(root))
            for invalid in ('broken JSON', '[]', '{}'):
                receipt.write_text(invalid)
                self.assertTrue(build_players.game_rebuild_required(root))
            (root/build_players.CLIENT).unlink()
            self.assertTrue(build_players.game_rebuild_required(root))

    def test_android_does_not_require_desktop_player_or_nsis(self):
        mocks = self.run_platform(['android'])
        mocks['signing'].assert_called_once()
        self.assertNotIn('makensis', [call.args[0] for call in mocks['which'].call_args_list])
        calls = mocks['run'].call_args_list
        self.assertTrue(any('android/build.py' in call.args[0] for call in calls))
        self.assertTrue(all('test-secret' not in call.args[0] for call in calls))

    def test_windows_requires_nsis_but_not_android_signing(self):
        mocks = self.run_platform(['windows'])
        mocks['signing'].assert_not_called()
        self.assertIn('makensis', [call.args[0] for call in mocks['which'].call_args_list])
