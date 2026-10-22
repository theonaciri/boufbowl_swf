"""Compile or run shared regressions against desktop/Android roots in native AIR."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from tools.build_tools import air_sdk
from tools.client_probe import build_probe
from tools.game_config import ROOT

LICENSE_ERROR = 'Linux runtime is limited to use by commercially licensed developers'


def inspect_native_result(text, returncode):
    if LICENSE_ERROR in text:
        return 'blocked', 'AIR requires a commercial developer license; no application code ran'
    if 'Error loading the runtime' in text or 'error while loading shared libraries' in text:
        return 'blocked', text.strip().splitlines()[0][:240]
    required = ('SHARED_SMOKE PASS:', 'SHARED_SMOKE REPLAY PASS',
                'fps=30 Playback mode 3D', 'Outgoing ResolutionDoneMessage', 'Incoming MATCH_END')
    missing = [marker for marker in required if marker not in text]
    if returncode or missing or 'SHARED_SMOKE FAIL:' in text:
        return 'failed', 'Native smoke failed; missing: '+', '.join(missing)
    return 'passed', None


def run_native(client, mode, args, sdk, evidence):
    log = evidence/('native-'+mode+'.log')
    with tempfile.TemporaryDirectory(prefix='native-'+mode+'-', dir=evidence) as temporary:
        work = Path(temporary)
        (work/'bin').mkdir()
        (work/'assets').symlink_to(ROOT/'assets', target_is_directory=True)
        shutil.copytree(ROOT/'resources', work/'resources')
        shutil.copyfile(args.fixture, work/'resources/mock_match.json')
        shutil.copyfile(client, work/'bin/client.swf')
        descriptor = work/'application.xml'
        descriptor.write_text(f'''<application xmlns="http://ns.adobe.com/air/application/51.1">
<id>org.boufbowl.sharedsmoke.{mode}{time.time_ns()}</id><versionNumber>1.0.0</versionNumber><filename>Shared Client Smoke</filename>
<initialWindow><content>bin/client.swf</content><visible>true</visible><width>1024</width><height>600</height><renderMode>cpu</renderMode></initialWindow>
<supportedProfiles>desktop</supportedProfiles></application>''')
        env = dict(os.environ)
        if args.runtime_libs:
            env['LD_LIBRARY_PATH'] = str(args.runtime_libs.resolve())+(os.pathsep+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
        command = [str(sdk/'bin/adl'), '-profile', 'desktop', str(descriptor), str(work)]
        if not env.get('DISPLAY'):
            command = ['xvfb-run', '-a', *command]
        try:
            with log.open('w') as stream:
                result = subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=args.timeout)
        except subprocess.TimeoutExpired:
            return {'status':'failed', 'reason':'Native playback timed out', 'log':str(log)}
        status, reason = inspect_native_result(log.read_text(), result.returncode)
        return {'status':status, 'reason':reason, 'log':str(log)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', choices=('desktop','android','both'), default='both')
    parser.add_argument('--compile-only', action='store_true', help='Compile both roots without running or requiring AIR')
    parser.add_argument('--air-sdk', type=Path)
    parser.add_argument('--fixture', type=Path, default=ROOT/'resources/mock_match.json')
    parser.add_argument('--runtime-libs', type=Path)
    parser.add_argument('--timeout', type=int, default=120)
    parser.add_argument('--output', type=Path, default=ROOT/'.local/shared-client/report.json')
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    evidence = args.output.parent
    evidence.mkdir(parents=True, exist_ok=True)
    modes = ('desktop','android') if args.root == 'both' else (args.root,)
    results = []
    sdk = None
    try:
        if not args.compile_only:
            sdk = air_sdk(args.air_sdk)
            if not (sdk/'bin/adl').is_file():
                raise RuntimeError('AIR SDK has no host-compatible bin/adl')
        runtime_blocked = None
        for mode in modes:
            started = time.monotonic()
            client, reused = build_probe(mode, native=True)
            result = {'root':mode,'client':str(client),'reused':reused,'status':'compiled'}
            if not args.compile_only:
                outcome = ({'status':'blocked','reason':runtime_blocked} if runtime_blocked else
                           run_native(client, mode, args, sdk, evidence))
                result.update(outcome)
                if result['status'] == 'blocked':
                    runtime_blocked = result['reason']
            result['seconds'] = round(time.monotonic()-started,2)
            results.append(result)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        results.append({'status':'failed','reason':str(error)})
    statuses = {result['status'] for result in results}
    status = 'failed' if 'failed' in statuses else 'blocked' if 'blocked' in statuses else 'compiled' if args.compile_only else 'passed'
    report = {'status':status,'results':results,'report':str(args.output)}
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)
    return 1 if status == 'failed' else 77 if status == 'blocked' else 0


if __name__ == '__main__':
    raise SystemExit(main())
