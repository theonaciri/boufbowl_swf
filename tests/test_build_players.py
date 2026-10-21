"""Platform selection must avoid unrelated dependencies and keep secrets off argv."""
from contextlib import ExitStack, nullcontext
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from tools import build_players


class BuildPlayersTests(unittest.TestCase):
    def run_platform(self, selection):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        if 'linux' in selection or 'windows' in selection:
            (root/'bin').mkdir()
            (root/'bin/flashplayer_32_sa.exe').write_bytes(b'player')
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(build_players, 'ROOT', root))
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
