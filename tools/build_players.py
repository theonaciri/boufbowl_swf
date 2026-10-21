"""Build Windows, Linux and Android downloads under one CPU budget."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tools.build_parallel import build_budget, parallel
from tools.build_tools import BuildError, ffdec_jar, air_sdk, android_sdk, jdk_directory, remember_build_tools
from tools.refresh_website import refresh_website
from tools.android_signing import signing_credentials

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--air-sdk', type=Path, help='AIR SDK override; otherwise discover installed SDKs automatically')
    parser.add_argument('--android-sdk', type=Path, help='Android SDK override; otherwise discover installed SDKs automatically')
    parser.add_argument('--jdk', type=Path, help='JDK 17+ directory; otherwise use Java from the normal tool cache/PATH')
    parser.add_argument('--ffdec', type=Path)
    parser.add_argument('--server-url')
    parser.add_argument('--makensis')
    parser.add_argument('--keystore', type=Path)
    parser.add_argument('--jobs', type=int, help='Maximum total CPU jobs (default: all available CPUs)')
    parser.add_argument('--bun', default=os.environ.get('BUN') or shutil.which('bun') or 'bun')
    parser.add_argument('--no-website', action='store_true')
    args = parser.parse_args()
    if args.jobs is not None and args.jobs < 1:
        parser.error('--jobs must be positive')
    try:
        args.air_sdk = air_sdk(args.air_sdk)
        args.android_sdk = android_sdk(args.android_sdk)
        jdk = jdk_directory(args.jdk)
        java = jdk/('bin/java.exe' if os.name == 'nt' else 'bin/java')
        ffdec = ffdec_jar(args.ffdec, download=True)
    except BuildError as error:
        parser.error(str(error))
    makensis = shutil.which(args.makensis or 'makensis')
    if not makensis:
        raise BuildError('NSIS compiler (makensis) is missing. Ubuntu/Debian: sudo apt install nsis. Arch: sudo pacman -S nsis.')
    if not shutil.which('ffmpeg'):
        raise BuildError('FFmpeg is missing; install ffmpeg before packaging players.')
    if not (ROOT/'bin/flashplayer_32_sa.exe').is_file():
        raise BuildError('Desktop Flash player missing: bin/flashplayer_32_sa.exe')
    _, password = signing_credentials(jdk, args.keystore)
    remember_build_tools(**{'AIR SDK': args.air_sdk, 'Android SDK': args.android_sdk, 'JDK': jdk})
    print(f'AIR SDK: {args.air_sdk}\nAndroid SDK: {args.android_sdk}\nJDK: {jdk}\nFFDec: {ffdec}', flush=True)
    desktop = [sys.executable, '-m', 'tools.build_player_downloads', '--java', java,
               '--ffdec', ffdec, '--no-website']
    android = [sys.executable, 'android/build.py', '--jdk', jdk, '--ffdec', ffdec,
               '--air-sdk', args.air_sdk, '--android-sdk', args.android_sdk, '--no-website']
    if args.server_url:
        desktop += ['--server-url', args.server_url]
        android += ['--server-url', args.server_url]
    desktop += ['--makensis', makensis]
    if args.keystore:
        android += ['--keystore', args.keystore]
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
        subprocess.run([str(args.bun), str(ROOT/'tools/build.mjs'), '--game-only',
                        '--java', str(java), '--ffdec', str(ffdec)], cwd=ROOT, check=True)
        # Coordinators do not reserve CPU permits; their leaf encoders/packagers do.
        failures = [failure for failure in parallel(package, [('Windows/Linux', desktop), ('Android', android)], workers=2) if failure]
        if failures:
            raise BuildError('Player builds failed: '+', '.join(failures)+'. See the errors above; completed downloads are preserved.')
        if not args.no_website:
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
