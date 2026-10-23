"""Cross-platform patch selection, generated roots, caches and honest reports."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import play

from tools.client_patches import client_patches
from tools.client_runtime_codegen import client_root_source
from tools.client_probe import compile_probe, probe_root, replace_once
from tools.smoke_shared_client import LICENSE_ERROR, inspect_native_result
from tools.verify_client import run_checks
from tools.runtime_fps_probe import runtime_probe_source, build_runtime_probe


class ClientToolingTests(unittest.TestCase):
    def test_blank_probe_launcher_requires_no_backend_import_or_service(self):
        root=Path(play.__file__).resolve().parent
        server=SimpleNamespace(server_address=('127.0.0.1',9919),serve_forever=lambda:None,
                               shutdown=lambda:None,server_close=lambda:None)
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ,{'XDG_DATA_HOME':directory,'XDG_STATE_HOME':directory}), \
             patch.dict(sys.modules,{'backend.server':None,'backend.service':None}), \
             patch('sys.argv',['play.py','--mode','server','--fps-probe','240']), \
             patch('tools.runtime_fps_probe.build_runtime_probe',return_value=(root/'bin/base/boufbowl-client-1.9.6.swf',True)), \
             patch.object(play.shutil,'which',return_value='/tools/wine'), \
             patch.object(play,'ThreadingHTTPServer',return_value=server), \
             patch.object(play.threading,'Thread'), \
             patch.object(play.subprocess,'run'), \
             patch.object(play.subprocess,'call',return_value=0) as launch:
            self.assertEqual(play.main(),0)
            self.assertIsNone(server.service)
            self.assertIn('server=0',launch.call_args.args[0][-1])

    def test_blank_runtime_probe_validates_target_and_does_not_boot_the_game(self):
        for invalid in (24,1001,float('nan'),float('inf'),-float('inf')):
            with self.assertRaises(ValueError):
                runtime_probe_source(invalid)
        for target in (25,60,120,240,1000):
            source = runtime_probe_source(target)
            self.assertNotIn('MainApp',source)
            self.assertNotIn('Service',source)
            self.assertIn('fpsProbeStats',source)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch('tools.runtime_fps_probe.compile_probe',return_value=('probe.swf',True)) as compiler:
                build_runtime_probe(240,root)
                self.assertEqual(compiler.call_args.args[0],root/'bin/base/boufbowl-client-1.9.6.swf')
                (root/'bin').mkdir()
                (root/'bin/boufbowl-client-1.9.6.swf').write_bytes(b'client')
                build_runtime_probe(240,root)
                self.assertEqual(compiler.call_args.args[0],root/'bin/boufbowl-client-1.9.6.swf')

    def test_shared_additions_reach_both_builds_and_android_overrides_only_its_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ('patches','android/patches'):
                (root/folder).mkdir(parents=True)
            for filename in ('patches/NewPatch.as','patches/Root.as','android/patches/Root.as'):
                (root/filename).write_text('package game { public class '+Path(filename).stem+' {} }')
            desktop = {p.class_name:p.source for p in client_patches(root)}
            android = {p.class_name:p.source for p in client_patches(root,'android')}
            self.assertEqual(desktop['game.NewPatch'],android['game.NewPatch'])
            self.assertEqual(desktop['game.Root'],root/'patches/Root.as')
            self.assertEqual(android['game.Root'],root/'android/patches/Root.as')
            (root/'android/patches/Root.as').write_text('package other { public class Root {} }')
            with self.assertRaisesRegex(ValueError,'changes the package'):
                client_patches(root,'android')

    def test_bad_patch_declarations_fail_before_building(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'patches').mkdir()
            (root/'patches/A.as').write_text('package game { public class B {} }')
            with self.assertRaisesRegex(ValueError,'Invalid AS3'):
                client_patches(root)
        with self.assertRaisesRegex(ValueError,'Unknown client platform'):
            client_patches(platform='invalid')

    def test_checked_in_roots_expand_and_probe_anchors_are_valid(self):
        for platform in ('desktop','android'):
            source = next(p.source for p in client_patches(platform=platform) if p.source.stem == 'BoufbowlClient')
            expanded = client_root_source(source.read_text())
            self.assertNotIn('@shared-client-runtime',expanded)
            with self.assertRaises(ValueError):
                client_root_source(expanded)
            for native in (False,True):
                instrumented = probe_root(platform,native)
                self.assertIn('runSharedSmoke',instrumented)
                self.assertNotIn('@shared-client-runtime',instrumented)
        with self.assertRaisesRegex(ValueError,'Probe anchor changed'):
            replace_once('twice twice','twice','replacement')

    def test_incremental_probes_reuse_content_and_rebuild_tampered_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = root/'base.swf';base.write_bytes(b'base')
            java = root/'java';java.write_bytes(b'java')
            jar = root/'ffdec.jar';jar.write_bytes(b'ffdec')
            def compile(command, **_):
                Path(command[5]).write_bytes(b'compiled')
                return subprocess.CompletedProcess(command,0)
            with patch('tools.client_probe.java_binary',return_value=java), \
                 patch('tools.client_probe.ffdec_jar',return_value=jar), \
                 patch('tools.package_cache.Inputs.java',return_value={'version':'test'}), \
                 patch('tools.client_probe.subprocess.run',side_effect=compile) as compiler:
                first, reused = compile_probe(base,[('game.Root','source')],root)
                self.assertFalse(reused)
                self.assertTrue(compile_probe(base,[('game.Root','source')],root)[1])
                first.write_bytes(b'tampered')
                self.assertFalse(compile_probe(base,[('game.Root','source')],root)[1])
                self.assertFalse(compile_probe(base,[('game.Root','changed')],root)[1])
                self.assertEqual(compiler.call_count,3)

    def test_license_gate_and_incomplete_native_replays_never_pass(self):
        self.assertEqual(inspect_native_result(LICENSE_ERROR,1)[0],'blocked')
        self.assertEqual(inspect_native_result('Error loading the runtime (libxml2.so.2: missing)',1)[0],'blocked')
        self.assertEqual(inspect_native_result('SHARED_SMOKE PASS:',0)[0],'failed')
        complete = '\n'.join(('SHARED_SMOKE PASS:', 'SHARED_SMOKE REPLAY PASS',
                              'fps=30 Playback mode 3D', 'Outgoing ResolutionDoneMessage','Incoming MATCH_END'))
        self.assertEqual(inspect_native_result(complete,0)[0],'passed')
        self.assertEqual(inspect_native_result(complete,1)[0],'failed')

    def test_compact_reports_preserve_failure_output_and_blocked_status(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            report = run_checks([('failure',[sys.executable,'-c','print("diagnostic");raise SystemExit(1)'])],output)
            self.assertEqual(report['status'],'failed')
            self.assertIn('diagnostic',report['checks'][0]['detail'])
            self.assertIn('diagnostic',(output/'failure.log').read_text())
            report = run_checks([('native',[sys.executable,'-c','raise SystemExit(77)'])],output)
            self.assertEqual(report['status'],'blocked')
            payload = json.dumps({'status':'blocked','results':[{'reason':'AIR license required'}],'report':'native.json'})
            report = run_checks([('native',[sys.executable,'-c',f'print({payload!r});raise SystemExit(77)'])],output)
            self.assertEqual(report['checks'][0]['detail'],'AIR license required')
            self.assertEqual(report['checks'][0]['evidence'],'native.json')
