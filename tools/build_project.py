"""Prepare missing game/media inputs, then compile the static website with Bun."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tools.build_tools import BuildError, ffdec_jar, java_binary

ROOT = Path(__file__).resolve().parent.parent


def run(command, label, env, cwd=ROOT):
    print(f'\n{label}', flush=True)
    result = subprocess.run([str(part) for part in command], cwd=cwd, env=env)
    if result.returncode:
        raise BuildError(f'{label} failed. Build stopped; fix the error above and rerun the same command.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'.local/website/dist')
    parser.add_argument('--ffdec', help='Optional FFDec JAR override; otherwise found/downloaded automatically')
    parser.add_argument('--java', help='Optional Java 17+ executable override')
    parser.add_argument('--game-only', action='store_true', help='Prepare the game without building the website')
    parser.add_argument('--rebuild-game', action='store_true', help='Recompile the game even if its SWF already exists')
    parser.add_argument('--refresh-media', action='store_true', help='Refresh existing media using the exporters’ caches')
    args = parser.parse_args()
    env = dict(os.environ)
    bun = env.get('BUN') or shutil.which('bun')
    if not bun:
        raise BuildError('Bun is missing. Install Bun, then run bun run build.')
    python = sys.executable
    client = ROOT/'bin/boufbowl-client-1.9.6.swf'
    rebuilt = args.rebuild_game or not client.is_file()
    java = ffdec = None

    def tools():
        nonlocal java, ffdec
        if java is None:
            java = java_binary(args.java)
            ffdec = ffdec_jar(args.ffdec, download=True)
            env.update(JAVA=str(java), FFDEC_JAR=str(ffdec), BUN=str(bun))
            env['PATH'] = str(java.parent) + os.pathsep + env.get('PATH', '')
            print(f'Java: {java}\nFFDec: {ffdec}', flush=True)

    if rebuilt:
        if not (ROOT/'bin/base/boufbowl-client-1.9.6.swf').is_file():
            raise BuildError('Required preserved input is missing: bin/base/boufbowl-client-1.9.6.swf. Restore it from Git.')
        tools()
        run([python, '-m', 'tools.game_config'], 'Validate game configuration', env)
        run([python, 'patches/rebuild.py', '--ffdec', ffdec], 'Build game client', env)
    else:
        print('Using existing game client (bun run build:game recompiles it).', flush=True)
    source = ROOT/'backend/engine_base.json'
    target = ROOT/'backend/build/engine_base.json'
    if not target.is_file() or target.read_bytes() != source.read_bytes():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    if rebuilt or not (ROOT/'resources/mock_match.json').is_file():
        run([python, '-m', 'tools.build_mock_fixture'], 'Prepare game runtime files', env)
    if not (ROOT/'assets/site/restoration/inventory.json').is_file():
        run([python, '-m', 'tools.build_restoration_data'], 'Prepare game resource inventory', env)
    if args.game_only:
        print('\nGame ready: bin/boufbowl-client-1.9.6.swf', flush=True)
        return

    from tools.build_restoration_data import homepage_assets
    missing = [row['path'] for row in homepage_assets(ROOT) if not row['available']]
    metadata_missing = any(not (ROOT/name).is_file() for name in (
        'assets/site/restoration/inventory.json', 'assets/site/restoration/portraits.json'))
    generate = args.refresh_media or bool(missing) or metadata_missing
    required = [name for name in ('ffmpeg', 'avifenc') if not shutil.which(name)]
    if required:
        raise BuildError('Missing media tools: ' + ', '.join(required) + '. Ubuntu/Debian: sudo apt install ffmpeg libavif-bin. Arch: sudo pacman -S ffmpeg libavif.')
    if generate:
        tools()
        print('\nGenerating missing website media. First builds can take a long time; completed captures are cached.', flush=True)
        renderer = ROOT/'tools/website'
        run([bun, 'install', '--frozen-lockfile'], 'Install website renderer dependencies', env, renderer)
        run([bun, 'x', '--bun', 'playwright', 'install', 'chromium'], 'Prepare headless Chromium', env, renderer)
        run([python, '-m', 'tools.build_restoration_data'], 'Prepare restoration inventory', env)
        tutorial = ('assets/site/tutorial-archive.mp4', 'assets/site/tutorial-field.mp4', 'assets/site/tutorial-poster.avif')
        if args.refresh_media or any(not (ROOT/name).is_file() for name in tutorial):
            run([python, '-m', 'tools.build_site_videos'], 'Generate tutorial videos', env)
        if args.refresh_media or any(name.startswith('assets/site/cinematic-') for name in missing):
            run([python, '-m', 'tools.export_home_cinematics'], 'Generate carousel cinematics', env)
        if args.refresh_media or any(name.startswith('assets/site/restoration/puppets/') for name in missing):
            run([python, '-m', 'tools.export_puppet_videos', '--java', java, '--ffdec', ffdec, '--bun', bun], 'Generate character videos', env)
        run([python, '-m', 'tools.build_website', '--java', java, '--ffdec', ffdec, '--bun', bun, '--output', args.output], 'Generate portraits and compile website', env)
    else:
        run([bun, ROOT/'tools/website/build.mjs', '--output', args.output], 'Compile static website', env)
    print(f'\nWebsite ready: {args.output.resolve()}', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (BuildError, OSError, ValueError) as error:
        print(f'\nBuild stopped: {error}', file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('\nBuild interrupted. Rerun the same command to continue.', file=sys.stderr)
        sys.exit(130)
