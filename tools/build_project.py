"""Prepare missing game/media inputs, then compile the static website with Bun."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tools.build_parallel import build_budget, available_cpus, parallel
from tools.build_tools import BuildError, ffdec_jar, java_binary

ROOT = Path(__file__).resolve().parent.parent


def run(command, label, env, cwd=ROOT):
    print(f'\n{label}', flush=True)
    result = subprocess.run([str(part) for part in command], cwd=cwd, env=env)
    if result.returncode:
        raise BuildError(f'{label} failed. Build stopped; fix the error above and rerun the same command.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', type=int, help='Maximum CPU jobs (default: all available CPUs)')
    parser.add_argument('--output', type=Path, default=ROOT/'.local/website/dist')
    parser.add_argument('--ffdec', help='Optional FFDec JAR override; otherwise found/downloaded automatically')
    parser.add_argument('--java', help='Optional Java 17+ executable override')
    parser.add_argument('--game-only', action='store_true', help='Prepare the game without building the website')
    parser.add_argument('--rebuild-game', action='store_true', help='Recompile the game even if its SWF already exists')
    args = parser.parse_args()
    if args.jobs is not None and args.jobs < 1:
        parser.error('--jobs must be positive')
    if args.jobs:
        os.environ['BOUFBOWL_BUILD_CPUS'] = str(min(args.jobs, available_cpus()))
    with build_budget(args.jobs):
        build(args)


def build(args):
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
        print('Using existing game client (bun run build recompiles it).', flush=True)
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
    from tools.website_media_cache import MediaCache
    cache = MediaCache(ROOT)
    shared = ['bin/boufbowl-client-1.9.6.swf', 'resources/game_config.json',
              'resources/palettes.json', 'resources/local_ui.json', 'resources/cosmetic_catalog.json',
              'tools/game_config.py', 'tools/mock_codegen.py', 'tools/server_codegen.py',
              'tools/visual_assets.py', 'tools/media_fingerprints.py', 'tools/build_parallel.py', 'tools/website/cpu-budget.mjs', 'patches/*.as', 'patches/*.inc',
              'assets/artworks/*.swf', 'assets/sprites/**/*', 'vendor/ruffle/*']
    stages = {
        'images': (['tools/convert_site_avif.py', 'tools/media_fingerprints.py', 'tools/build_parallel.py', 'resources/stadium_art.json',
                    'assets/site/logo.webp', 'assets/textures/stadiums/*.png'],
                   ['assets/textures/stadiums/*.avif', 'assets/site/logo.avif']),
        'tutorial': (['tools/build_site_videos.py', 'tools/build_parallel.py', 'assets/videos/tutorial-intro.flv',
                      'assets/videos/layout_tuto_01.flv'],
                     ['assets/site/tutorial-archive.mp4', 'assets/site/tutorial-field.mp4', 'assets/site/tutorial-poster.avif']),
        'cinematics': (shared + ['tools/export_home_cinematics.py', 'tools/site_cinematic_capture.as.inc', 'tools/website/cinematics.mjs'],
                       ['assets/site/cinematic-*.mp4', 'assets/site/cinematic-*.avif', 'docs/site/media-sources.json']),
        'puppets': (shared + ['tools/export_puppet_videos.py', 'tools/site_puppet_capture.as.inc', 'tools/website/puppet-videos.mjs', 'tools/site_portraits.py'],
                    ['assets/site/restoration/puppets/*.mp4', 'assets/site/restoration/puppets/videos.json']),
        'portraits': (shared + ['tools/build_website.py', 'tools/site_portraits.py', 'tools/site_portrait_capture.*',
                                'tools/site_grid_icons.py', 'tools/website/render.mjs',
                                'tools/build_restoration_data.py', 'resources/stadium_art.json', 'resources/stadiums.json',
                                'resources/sound.json', 'assets/sounds/**/*'],
                      ['assets/site/restoration/portraits.json', '.local/website/portrait-cache.json',
                       'assets/site/restoration/*-*.webp', 'assets/site/restoration/grid-icons/*.png']),
    }
    reasons = {name: cache.reason(name, inputs, outputs) for name, (inputs, outputs) in stages.items()}
    missing = [row['path'] for row in homepage_assets(ROOT) if not row['available']]
    # Also repair referenced files absent from an otherwise intact cached stage.
    for name in missing:
        if name.startswith('assets/site/cinematic-'):
            stage = 'cinematics'
        elif name.startswith('assets/site/restoration/puppets/'):
            stage = 'puppets'
        elif name == 'assets/site/logo.avif' or name.startswith('assets/textures/stadiums/'):
            stage = 'images'
        elif name.startswith('assets/site/tutorial-'):
            stage = 'tutorial'
        else:
            stage = 'portraits'
        reasons[stage] = 'referenced asset missing: ' + name
    dirty = {name: reason is not None for name, reason in reasons.items()}
    if any(dirty.values()):
        print('\nUpdating changed or missing website media; completed stages are cached.', flush=True)
        for name, reason in reasons.items():
            if reason:
                print(f'  {name}: {reason}', flush=True)
        required = [name for name in ('ffmpeg', 'avifenc') if not shutil.which(name)]
        if required:
            raise BuildError('Missing media tools: ' + ', '.join(required) + '. Ubuntu/Debian: sudo apt install ffmpeg libavif-bin. Arch: sudo pacman -S ffmpeg libavif.')
        if any(dirty[name] for name in ('cinematics', 'puppets', 'portraits')):
            tools()
            renderer = ROOT/'tools/website'
            run([bun, 'install', '--frozen-lockfile'], 'Prepare website renderer dependencies', env, renderer)
            run([bun, 'x', '--bun', 'playwright', 'install', 'chromium'], 'Prepare headless Chromium', env, renderer)
        run([python, '-m', 'tools.build_restoration_data'], 'Prepare restoration inventory', env)
        commands = {
            'images': [python, '-m', 'tools.convert_site_avif'],
            'tutorial': [python, '-m', 'tools.build_site_videos'],
            'cinematics': [python, '-m', 'tools.export_home_cinematics'],
            'puppets': [python, '-m', 'tools.export_puppet_videos', '--java', java, '--ffdec', ffdec, '--bun', bun],
            'portraits': [python, '-m', 'tools.build_website', '--java', java, '--ffdec', ffdec, '--bun', bun, '--skip-images', '--assets-only', '--output', args.output],
        }
        def update(item):
            name, command = item
            run(command, 'Update website ' + name, env)
            return name
        for name in parallel(update, [(name, command) for name, command in commands.items() if dirty[name]]):
            cache.save(name, *stages[name])
        for name in commands:
            if not dirty[name]:
                print('Reusing website ' + name, flush=True)
    else:
        print('Website media unchanged; reusing all exports.', flush=True)
    if any(dirty.values()):
        run([python, '-m', 'tools.build_restoration_data'], 'Refresh restoration inventory', env)
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
