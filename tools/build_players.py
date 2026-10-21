"""Build Windows, Linux and Android downloads under one CPU budget."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tools.build_parallel import build_budget, parallel
from tools.build_tools import ffdec_jar, java_binary
from tools.refresh_website import refresh_website

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--air-sdk', type=Path, default=os.environ.get('AIR_SDK'))
    parser.add_argument('--android-sdk', type=Path, default=Path(os.environ.get('ANDROID_HOME', Path.home()/'Android/Sdk')))
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
    if not args.air_sdk or not (args.air_sdk/'lib/adt.jar').is_file():
        parser.error('Pass --air-sdk /path/to/AIRSDK or set AIR_SDK to an installed AIR SDK.')
    if not args.android_sdk.is_dir():
        parser.error('Pass --android-sdk /path/to/Android/Sdk or set ANDROID_HOME.')
    java = java_binary(args.jdk/'bin/java' if args.jdk else None)
    jdk = args.jdk or java.resolve().parent.parent
    if not (jdk/'bin/javac').is_file():
        parser.error('Android packaging needs a full JDK; pass --jdk /path/to/jdk-17.')
    ffdec = ffdec_jar(args.ffdec, download=True)
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
