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
    remember_build_tools(**{'AIR SDK': args.air_sdk, 'Android SDK': args.android_sdk, 'JDK': jdk})
    print(f'AIR SDK: {args.air_sdk}\nAndroid SDK: {args.android_sdk}\nJDK: {jdk}\nFFDec: {ffdec}', flush=True)
    desktop = [sys.executable, '-m', 'tools.build_player_downloads', '--java', java,
               '--ffdec', ffdec, '--no-website']
    android = [sys.executable, 'android/build.py', '--jdk', jdk, '--ffdec', ffdec,
               '--air-sdk', args.air_sdk, '--android-sdk', args.android_sdk, '--no-website']
    if args.server_url:
        desktop += ['--server-url', args.server_url]
        android += ['--server-url', args.server_url]
    if args.makensis:
        desktop += ['--makensis', args.makensis]
    if args.keystore:
        android += ['--keystore', args.keystore]
    def package(command):
        subprocess.run([str(part) for part in command], cwd=ROOT, check=True)
    with build_budget(args.jobs):
        subprocess.run([str(args.bun), str(ROOT/'tools/build.mjs'), '--game-only',
                        '--java', str(java), '--ffdec', str(ffdec)], cwd=ROOT, check=True)
        # Coordinators do not reserve CPU permits; their leaf encoders/packagers do.
        for _ in parallel(package, [desktop, android], workers=2):
            pass
        if not args.no_website:
            refresh_website(ROOT, args.bun)


if __name__ == '__main__':
    main()
