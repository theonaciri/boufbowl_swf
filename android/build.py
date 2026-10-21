#!/usr/bin/env python3
"""Package the patched Flash client and its assets with the Android AIR runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.build_parallel import build_budget, cpu_run, parallel
from tools.game_config import DEFAULT_CONFIG, apply_resources, flashvars_source, load_config, startup_source
from tools.visual_assets import palette_item_source
from tools.player_server import player_server
from tools.player_branding import build_icons
from tools.player_assets import ignore_website_stadium_previews


def run(command, *, env=None, timeout=600):
    try:
        cpu_run([str(arg) for arg in command], check=True, env=env, timeout=timeout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        # Packaging arguments contain the signing password.
        raise RuntimeError("Build command failed: " + Path(command[0]).name) from None


def local_signing_password(certificate):
    """Keep the local signing password beside the certificate, outside Git."""
    override = os.environ.get("BOUFBOWL_KEYSTORE_PASSWORD")
    if override:
        return override
    password_file = certificate.with_suffix(".password")
    if password_file.is_file():
        password = password_file.read_text().strip()
        if not password:
            raise ValueError("The local signing password file is empty.")
        password_file.chmod(0o600)
        return password
    if certificate.exists():
        raise ValueError("Existing signing certificate needs BOUFBOWL_KEYSTORE_PASSWORD or its local .password file. Keep the certificate to preserve app updates.")
    password = secrets.token_urlsafe(32)
    descriptor = os.open(password_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        output.write(password + "\n")
    return password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, help="Maximum CPU jobs (default: available CPUs)")
    parser.add_argument("--air-sdk", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--ffdec", type=Path, required=True)
    parser.add_argument("--android-sdk", type=Path, default=Path.home() / "Android/Sdk")
    parser.add_argument("--jdk", type=Path, required=True, help="JDK 17 or newer directory")
    parser.add_argument("--arch", choices=("armv8", "x64"), default="armv8")
    parser.add_argument("--server-url", help="Override resources/site.json hosted server")
    parser.add_argument("--debug", action="store_true", help="Include AIR's debugger runtime")
    parser.add_argument("--keystore", type=Path, help="Optional PKCS12 signing certificate")
    parser.add_argument('--bun', default='bun', help='Bun executable for refreshing the website')
    parser.add_argument('--no-website', action='store_true', help='Build the APK only; defer website generation')
    args = parser.parse_args()
    if args.jobs is not None and args.jobs < 1:
        parser.error('--jobs must be positive')
    with build_budget(args.jobs):
        build(args, parser)


def build(args, parser):
    android = Path(__file__).resolve().parent
    root = android.parent
    try:
        args.server_url = player_server(root, args.server_url)
    except ValueError as error:
        parser.error(str(error))
    game_config = load_config(args.config)
    game_config['general']['startup_mode'] = 'server'
    build = android / "build"
    stage = build / "package"
    stage.mkdir(parents=True, exist_ok=True)
    (stage / "bin").mkdir(exist_ok=True)
    for name in ("assets", "resources"):
        target = stage / name
        if target.exists():
            shutil.rmtree(target)
        # Website portraits and promotional media are not used by the game.
        shutil.copytree(root / name, target, ignore=lambda directory, names: (
            set(ignore_website_stadium_previews(directory, names))
            | ({"site"} & set(names) if Path(directory) == root / "assets" else set())
        ))
    build_icons(root, stage/"icons")
    apply_resources(stage / "resources", game_config)
    # Android's VP6 decoder produces artifacts on these legacy FLV clips.
    # Cache H.264/AAC copies; all original media stays intact in the desktop tree.
    video_cache = build / "video-cache"
    video_cache.mkdir(exist_ok=True)
    def encode_video(source):
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        cached = video_cache / (source.stem + ".mp4")
        stamp = video_cache / (source.stem + ".sha256")
        if not cached.exists() or not stamp.exists() or stamp.read_text() != digest:
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", source,
                 "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264",
                 "-profile:v", "baseline", "-level", "3.1", "-pix_fmt", "yuv420p",
                 "-crf", "18", "-preset", "fast", "-c:a", "aac", "-b:a", "128k",
                 "-movflags", "+faststart", cached])
            stamp.write_text(digest)
        target = stage / "assets/videos" / cached.name
        shutil.copyfile(cached, target)
        (stage / "assets/videos" / source.name).unlink()
    for _ in parallel(encode_video, (root/"assets/videos").glob("*.flv")):
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

    java = args.jdk.resolve() / "bin/java"
    env = dict(os.environ, JAVA_HOME=str(args.jdk.resolve()))
    adt = args.air_sdk.resolve() / "lib/adt.jar"
    swf_name = "boufbowl-client-1.9.6.swf"
    replacements = []
    sources_by_name = {source.name: source for source in (root / "patches").glob("*.as")}
    sources_by_name.update({source.name: source for source in (android / "patches").glob("*.as")})
    sources = sorted(sources_by_name.values())
    for source in sources:
        text = source.read_text()
        package = re.search(r"\bpackage\s+([\w.]+)", text).group(1)
        replacements.extend([package + "." + source.stem, source])
    with tempfile.TemporaryDirectory(prefix=".configured-patches-", dir=build) as temporary:
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
        run([java, "-jar", args.ffdec.resolve(), "-replace", root / "bin" / swf_name,
             stage / "bin" / swf_name, *replacements], timeout=600)

    if args.keystore:
        certificate = args.keystore.resolve()
        password = os.environ.get("BOUFBOWL_KEYSTORE_PASSWORD")
        if not password:
            parser.error("Set BOUFBOWL_KEYSTORE_PASSWORD for your certificate.")
    else:
        cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        certificate = cache / "boufbowl-flash-tools/android-signing/local.p12"
        certificate.parent.mkdir(parents=True, exist_ok=True)
        try:
            password = local_signing_password(certificate)
        except ValueError as error:
            parser.error(str(error))
        if not certificate.exists():
            run([java, "-jar", adt, "-certificate", "-cn", "Boufbowl Fan",
                 "2048-RSA", certificate, password], env=env)
        certificate.chmod(0o600)
    suffix = "" if args.arch == "armv8" else "-emulator-x64"
    if args.debug:
        suffix += "-debug"
    output = build / ("Boufbowl Fan" + suffix + ".apk")
    temporary_output = output.with_name("." + output.stem + ".building.apk")
    run([java, "-Xmx2g", "-jar", adt, "-package", "-target", "apk-debug" if args.debug else "apk",
         "-arch", args.arch, "-storetype", "pkcs12", "-keystore", certificate,
         "-storepass", password, temporary_output, android / "application.xml",
         "-C", stage, "bin/" + swf_name, "assets", "resources", "icons",
         "-platformsdk", args.android_sdk.resolve()], env=env)
    temporary_output.replace(output)
    print("Built", output, "— default server:", args.server_url, flush=True)
    if not args.no_website:
        from tools.refresh_website import refresh_website
        refresh_website(root, args.bun)


if __name__ == "__main__":
    main()
