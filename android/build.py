#!/usr/bin/env python3
"""Package the patched Flash client and its assets with the Android AIR runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.build_parallel import build_budget, cpu_run, parallel
from tools.client_patches import client_patches
from tools.client_runtime_codegen import client_root_source
from tools.build_tools import BuildError, air_sdk, android_sdk, jdk_directory, ffdec_jar, remember_build_tools
from tools.game_config import DEFAULT_CONFIG, apply_resources, flashvars_source, load_config, startup_source
from tools.visual_assets import palette_item_source
from tools.package_cache import Inputs, Receipt, digest, copy_changed, sync_tree, runtime_identity
from tools.player_assets import website_stadium_preview
from tools.player_server import player_server
from tools.android_signing import signing_credentials
from tools.player_branding import build_icons
from tools.player_assets import ignore_website_stadium_previews


def run(command, *, env=None, timeout=600):
    try:
        cpu_run([str(arg) for arg in command], check=True, env=env, timeout=timeout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        # Packaging arguments contain the signing password.
        raise RuntimeError("Build command failed: " + Path(command[0]).name) from None


def runtime_options(*, debug=False, diagnostic=False):
    """Diagnostic builds must start without a connected desktop debugger."""
    if debug and diagnostic:
        raise ValueError('Choose --debug or --diagnostic, not both')
    return ['-target', 'apk-debug', '-listen', '7936'] if debug else ['-target', 'apk']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, help="Maximum CPU jobs (default: available CPUs)")
    parser.add_argument("--air-sdk", type=Path, help="Override automatic AIR SDK discovery")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--ffdec", type=Path, help="Override automatic FFDec discovery/download")
    parser.add_argument("--android-sdk", type=Path, help="Override automatic Android SDK discovery")
    parser.add_argument("--jdk", type=Path, help="Override automatic JDK 17+ discovery")
    parser.add_argument("--arch", choices=("armv8", "x64"), default="armv8")
    parser.add_argument("--server-url", help="Override resources/site.json hosted server")
    diagnostics = parser.add_mutually_exclusive_group()
    diagnostics.add_argument("--debug", action="store_true", help="Include AIR's debugger runtime; waits for USB debugger on port 7936")
    diagnostics.add_argument("--diagnostic", action="store_true", help="Include SWF debug locations with the normal runtime; starts without a debugger")
    parser.add_argument("--keystore", type=Path, help="Optional PKCS12 signing certificate")
    parser.add_argument('--bun', default='bun', help='Bun executable for refreshing the website')
    parser.add_argument('--no-website', action='store_true', help='Build the APK only; defer website generation')
    args = parser.parse_args()
    if args.jobs is not None and args.jobs < 1:
        parser.error('--jobs must be positive')
    try:
        args.air_sdk = air_sdk(args.air_sdk)
        args.android_sdk = android_sdk(args.android_sdk)
        args.jdk = jdk_directory(args.jdk)
        args.ffdec = ffdec_jar(args.ffdec, download=True)
    except BuildError as error:
        parser.error(str(error))
    remember_build_tools(**{'AIR SDK': args.air_sdk, 'Android SDK': args.android_sdk, 'JDK': args.jdk})
    with build_budget(args.jobs):
        build(args, parser)


def build(args, parser):
    root = Path(__file__).resolve().parent.parent
    with Receipt(root, 'android-build').lock():
        return build_locked(args, parser)


def build_locked(args, parser):
    android = Path(__file__).resolve().parent
    root = android.parent
    try:
        args.server_url = player_server(root, args.server_url)
    except ValueError as error:
        parser.error(str(error))
    certificate, password = signing_credentials(args.jdk, args.keystore)
    java = args.jdk.resolve() / 'bin/java'
    env = dict(os.environ, JAVA_HOME=str(args.jdk.resolve()))
    adt = args.air_sdk.resolve() / 'lib/adt.jar'
    if not certificate.exists():
        run([java, '-jar', adt, '-certificate', '-cn', 'Boufbowl Fan',
             '2048-RSA', certificate, password], env=env)
    if not args.keystore:
        certificate.chmod(0o600)
    game_config = load_config(args.config)
    game_config['general']['startup_mode'] = 'server'
    build = android / "build"
    build.mkdir(parents=True, exist_ok=True)
    suffix = '' if args.arch == 'armv8' else '-emulator-x64'
    if args.debug:
        suffix += '-debug'
    elif args.diagnostic:
        suffix += '-diagnostic'
    output = build/('Boufbowl Fan'+suffix+'.apk')
    inputs = Inputs()
    asset_root = root/'assets'
    game_assets = {path.relative_to(root).as_posix(): inputs.file(path)
                   for path in sorted(asset_root.rglob('*')) if path.is_file()
                   and not path.is_relative_to(asset_root/'site') and not website_stadium_preview(path)}
    tools = ['game_config', 'visual_assets', 'mock_codegen', 'server_codegen',
             'stadium_celebrations', 'power_descriptions', 'tournament_text',
             'player_assets', 'player_branding', 'package_cache']
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise BuildError('FFmpeg is required for Android media and icons')
    identity = {'recipe': inputs.file(Path(__file__)), 'runtime': runtime_identity(), 'assets': game_assets,
                'resources': inputs.tree(root/'resources'), 'config': inputs.file(args.config),
                'client': inputs.file(root/'bin/boufbowl-client-1.9.6.swf'),
                'patches': inputs.tree(android/'patches'),
                'patch_registry': inputs.file(root/'tools/client_patches.py'),
                'runtime_codegen': inputs.file(root/'tools/client_runtime_codegen.py'),
                'common_patches': {p.name: inputs.file(p) for p in sorted((root/'patches').iterdir()) if p.is_file()},
                'helpers': {name: inputs.file(root/('tools/'+name+'.py')) for name in tools},
                'descriptor': inputs.file(android/'application.xml'), 'server_url': args.server_url,
                'arch': args.arch, 'debug': args.debug, 'diagnostic': args.diagnostic,
                'certificate': inputs.file(certificate),
                'java': inputs.java(java), 'ffdec': inputs.tree(args.ffdec.parent),
                'air_lib': inputs.tree(args.air_sdk/'lib'), 'air_bin': inputs.tree(args.air_sdk/'bin'),
                'android_platforms': inputs.tree(args.android_sdk/'platforms'),
                'android_build_tools': inputs.tree(args.android_sdk/'build-tools'),
                'ffmpeg': inputs.tool(ffmpeg)}
    fingerprint = digest(identity)
    receipt = Receipt(root, 'package-android'+suffix)
    if receipt.current(fingerprint, [output]):
        print('Reusing Android package: '+output.name, flush=True)
        if not args.no_website:
            from tools.refresh_website import refresh_website
            refresh_website(root, args.bun)
        return output
    print('Preparing Android package', flush=True)
    stage = build / "package"
    stage.mkdir(parents=True, exist_ok=True)
    (stage / "bin").mkdir(exist_ok=True)
    video_sources = sorted((asset_root/'videos').glob('*.flv'))
    preserve = [source.relative_to(asset_root).with_suffix('.mp4') for source in video_sources]
    asset_stats = sync_tree(asset_root, stage/'assets',
                           include=lambda p: not p.is_relative_to(asset_root/'site')
                           and not website_stadium_preview(p) and p not in video_sources,
                           preserve=preserve)
    resource_stats = sync_tree(root/'resources', stage/'resources')
    print(f'Android staging: assets {asset_stats}; resources {resource_stats}', flush=True)
    build_icons(root, stage/"icons")
    apply_resources(stage / "resources", game_config)
    # Android's VP6 decoder produces artifacts on these legacy FLV clips.
    # Cache H.264/AAC copies; all original media stays intact in the desktop tree.
    video_cache = build / "video-cache"
    video_cache.mkdir(exist_ok=True)
    video_options = ['-map', '0:v:0', '-map', '0:a?', '-c:v', 'libx264',
                     '-profile:v', 'baseline', '-level', '3.1', '-pix_fmt', 'yuv420p',
                     '-crf', '18', '-preset', 'fast', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart']
    def encode_video(source):
        key = digest({'source': inputs.file(source), 'options': video_options, 'ffmpeg': identity['ffmpeg']})
        cached = video_cache/(source.stem+'.mp4')
        video_receipt = Receipt(root, 'android-video/'+source.stem)
        if not video_receipt.current(key, [cached]):
            temporary = cached.with_name('.'+cached.stem+'.building.mp4')
            run(['ffmpeg', '-y', '-loglevel', 'error', '-i', source, *video_options, temporary])
            temporary.replace(cached)
            video_receipt.save(key, [cached])
        copy_changed(cached, stage/'assets/videos'/cached.name)
    for _ in parallel(encode_video, video_sources):
        pass
    # AIR uses application URLs rather than the desktop HTTP server.
    for file in (stage / "resources").glob("*.json"):
        data = file.read_text(encoding="utf-8-sig")
        data = data.replace("../assets", "app:/assets").replace("../resources", "app:/resources")
        file.write_text(data)
    config_file = stage / "resources/config.json"
    config = json.loads(config_file.read_text())
    config["3dActivated"] = str(game_config["general"]["android_scene_3d"]).lower()
    config_file.write_text(json.dumps(config, indent=2) + "\n")
    # No remote logging socket is needed in an offline Android application.
    (stage / "resources/logback.xml").write_text(
        '<configuration><appender name="STDOUT" '
        'class="com.reider.log4AS3.appenders.ConsoleAppender"/>'
        '<root><level value="WARN"/><appender-ref ref="STDOUT"/>'
        '</root></configuration>')

    swf_name = "boufbowl-client-1.9.6.swf"
    replacements = []
    for patch in client_patches(root, 'android'):
        replacements.extend([patch.class_name, patch.source])
    with tempfile.TemporaryDirectory(prefix=".configured-patches-", dir=build) as temporary:
        client_root = Path(temporary) / "BoufbowlClient.as"
        client_root.write_text(client_root_source((android / "patches/BoufbowlClient.as").read_text(), root))
        for index in range(0, len(replacements), 2):
            if replacements[index] == "com.ankamagames.boufbowl.BoufbowlClient":
                replacements[index + 1] = client_root
        palette = Path(temporary) / "BoufbowlerPaletteItem.as"
        palette.write_text(palette_item_source((root / "patches/BoufbowlerPaletteItem.as").read_text()))
        startup = Path(temporary) / "StartUpApplicationCommand.as"
        startup.write_text(startup_source((android / "patches/StartUpApplicationCommand.as").read_text(), game_config, android=True, server_url=args.server_url))
        for index in range(0, len(replacements), 2):
            if replacements[index].endswith(".BoufbowlerPaletteItem"):
                replacements[index + 1] = palette
            if replacements[index].endswith(".StartUpApplicationCommand"):
                replacements[index + 1] = startup
        flashvars = Path(temporary) / "FlashVarsManager.as"
        flashvars.write_text(flashvars_source((root / "patches/FlashVarsManager.as").read_text(), game_config))
        replacements.extend(["com.ankamagames.xgaming.utils.flashvars.FlashVarsManager", flashvars])
        compile_key = digest({'client': identity['client'], 'ffdec': identity['ffdec'],
                              'java': identity['java'], 'recipe': 1,
                              'patches': [(replacements[i], inputs.file(replacements[i+1]))
                                          for i in range(0, len(replacements), 2)]})
        compile_receipt = Receipt(root, 'android-client/'+compile_key)
        compiled = root/'.local/player-clients/android'/compile_key/'client.swf'
        if not compile_receipt.current(compile_key, [compiled]):
            print('Compiling Android client', flush=True)
            compiled.parent.mkdir(parents=True, exist_ok=True)
            temporary_client = compiled.with_suffix('.building.swf')
            run([java, '-jar', args.ffdec.resolve(), '-replace', root/'bin'/swf_name,
                 temporary_client, *replacements], timeout=600)
            temporary_client.replace(compiled)
            compile_receipt.save(compile_key, [compiled])
        else:
            print('Reusing compiled Android client', flush=True)
        packaged_client = compiled
        if args.debug or args.diagnostic:
            # A debug AIR runtime alone does not enable SWF stack/line data.
            # Keep diagnostic bytecode separate from the release client cache.
            debug_key = digest({'compile': compile_key, 'debug_recipe': 1})
            debug_client = compiled.with_name('client-debug.swf')
            debug_receipt = Receipt(root, 'android-debug-client/'+debug_key)
            if not debug_receipt.current(debug_key, [debug_client]):
                temporary_debug = debug_client.with_suffix('.building.swf')
                run([java, '-jar', args.ffdec.resolve(), '-enabledebugging',
                     '-injectas3', '-pcode', compiled, temporary_debug], timeout=600)
                temporary_debug.replace(debug_client)
                debug_receipt.save(debug_key, [debug_client])
            packaged_client = debug_client
        copy_changed(packaged_client, stage/'bin'/swf_name)

    temporary_output = output.with_name("." + output.stem + ".building.apk")
    run([java, "-Xmx2g", "-jar", adt, "-package", *runtime_options(debug=args.debug, diagnostic=args.diagnostic),
         "-arch", args.arch, "-storetype", "pkcs12", "-keystore", certificate,
         "-storepass", password, temporary_output, android / "application.xml",
         "-C", stage, "bin/" + swf_name, "assets", "resources", "icons",
         "-platformsdk", args.android_sdk.resolve()], env=env)
    temporary_output.replace(output)
    receipt.save(fingerprint, [output])
    print("Built", output, "— default server:", args.server_url, flush=True)
    if not args.no_website:
        from tools.refresh_website import refresh_website
        refresh_website(root, args.bun)


if __name__ == "__main__":
    try:
        main()
    except (BuildError, RuntimeError, OSError) as error:
        print(f'Android build stopped: {error}', file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('Android build interrupted.', file=sys.stderr)
        sys.exit(130)
