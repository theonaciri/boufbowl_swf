"""Build Windows, Linux and Android downloads under one CPU budget."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tools.build_parallel import build_budget, parallel
from tools.build_tools import BuildError, ffdec_jar, air_sdk, android_sdk, jdk_directory, java_binary, remember_build_tools
from tools.refresh_website import refresh_website
from tools.android_signing import signing_credentials
from tools.game_build_state import game_rebuild_required
from tools.media_fingerprints import CLIENT

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', '--platforms', action='extend', nargs='+', choices=('windows', 'linux', 'android'),
                        help='Platforms to build (default: windows linux android; repeatable)')
    parser.add_argument('--air-sdk', type=Path, help='AIR SDK override; otherwise discover installed SDKs automatically')
    parser.add_argument('--android-sdk', type=Path, help='Android SDK override; otherwise discover installed SDKs automatically')
    parser.add_argument('--jdk', type=Path, help='JDK 17+ directory; otherwise use Java from the normal tool cache/PATH')
    parser.add_argument('--ffdec', type=Path)
    parser.add_argument('--server-url')
    parser.add_argument('--makensis')
    parser.add_argument('--keystore', type=Path)
    parser.add_argument('--jobs', type=int, help='Maximum total CPU jobs (default: all available CPUs)')
    parser.add_argument('--bun', default=os.environ.get('BUN') or shutil.which('bun') or 'bun')
    website = parser.add_mutually_exclusive_group()
    website.add_argument('--no-website', action='store_true')
    website.add_argument('--website-media', action='store_true', help='Also update changed website media (release workflow)')
    args = parser.parse_args()
    if args.jobs is not None and args.jobs < 1:
        parser.error('--jobs must be positive')
    selected = tuple(dict.fromkeys(args.platform or ('windows', 'linux', 'android')))
    desktops = [platform for platform in selected if platform in ('windows', 'linux')]
    includes_android = 'android' in selected
    remembered = {}
    try:
        if includes_android:
            args.air_sdk = air_sdk(args.air_sdk)
            args.android_sdk = android_sdk(args.android_sdk)
            jdk = jdk_directory(args.jdk)
            java = jdk/('bin/java.exe' if os.name == 'nt' else 'bin/java')
            remembered = {'AIR SDK': args.air_sdk, 'Android SDK': args.android_sdk, 'JDK': jdk}
        else:
            java = java_binary(args.jdk/('bin/java.exe' if os.name == 'nt' else 'bin/java') if args.jdk else None)
        ffdec = ffdec_jar(args.ffdec, download=True)
    except BuildError as error:
        parser.error(str(error))
    makensis = None
    if 'windows' in selected:
        makensis = shutil.which(args.makensis or 'makensis')
        if not makensis:
            raise BuildError('NSIS compiler (makensis) is missing. Ubuntu/Debian: sudo apt install nsis. Arch: sudo pacman -S nsis.')
    if not shutil.which('ffmpeg'):
        raise BuildError('FFmpeg is missing; install ffmpeg before packaging players.')
    if desktops and not (ROOT/'bin/flashplayer_32_sa.exe').is_file():
        raise BuildError('Desktop Flash player missing: bin/flashplayer_32_sa.exe')
    password = None
    if includes_android:
        _, password = signing_credentials(jdk, args.keystore)
        remember_build_tools(**remembered)
        print(f'AIR SDK: {args.air_sdk}\nAndroid SDK: {args.android_sdk}\nJDK: {jdk}', flush=True)
    print(f'Platforms: {", ".join(selected)}\nJava: {java}\nFFDec: {ffdec}', flush=True)
    jobs = []
    if desktops:
        desktop = [sys.executable, '-m', 'tools.build_player_downloads', '--java', java,
                   '--ffdec', ffdec, '--no-website', '--platform', *desktops]
        if args.server_url:
            desktop += ['--server-url', args.server_url]
        if makensis:
            desktop += ['--makensis', makensis]
        jobs.append(('/'.join(platform.title() for platform in desktops), desktop))
    if includes_android:
        android = [sys.executable, 'android/build.py', '--jdk', jdk, '--ffdec', ffdec,
                   '--air-sdk', args.air_sdk, '--android-sdk', args.android_sdk, '--no-website']
        if args.server_url:
            android += ['--server-url', args.server_url]
        if args.keystore:
            android += ['--keystore', args.keystore]
        jobs.append(('Android', android))
    def package(item):
        label, command = item
        env = dict(os.environ)
        if label == 'Android':
            env['BOUFBOWL_KEYSTORE_PASSWORD'] = password
        try:
            result = subprocess.run([str(part) for part in command], cwd=ROOT, env=env)
            if result.returncode:
                return f'{label} (exit {result.returncode})'
        except OSError as error:
            return f'{label}: {error}'
        return None
    with build_budget(args.jobs):
        prepare = [str(args.bun), str(ROOT/'tools/build.mjs'), '--game-only',
                   '--java', str(java), '--ffdec', str(ffdec)]
        if game_rebuild_required(ROOT):
            print('Game sources or compiled client changed; rebuilding before packaging.', flush=True)
            prepare.append('--rebuild-game')
        subprocess.run(prepare, cwd=ROOT, check=True)
        # Coordinators do not reserve CPU permits; their leaf encoders/packagers do.
        failures = [failure for failure in parallel(package, jobs, workers=len(jobs)) if failure]
        if failures:
            raise BuildError('Player builds failed: '+', '.join(failures)+'. See the errors above; completed downloads are preserved.')
        if args.website_media:
            command = [args.bun, str(ROOT/'tools/build.mjs')]
            if args.jobs is not None:
                command += ['--jobs', str(args.jobs)]
            subprocess.run(command, cwd=ROOT, check=True)
        elif not args.no_website:
            refresh_website(ROOT, args.bun)


if __name__ == '__main__':
    try:
        main()
    except (BuildError, OSError) as error:
        print(f'Build stopped: {error}', file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as error:
        print(f'Build stopped: {Path(str(error.cmd[0])).name} exited with code {error.returncode}. See the error above.', file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('Player build interrupted.', file=sys.stderr)
        sys.exit(130)
