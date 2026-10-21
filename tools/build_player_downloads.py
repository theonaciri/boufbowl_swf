"""Package local Windows/Linux clients and assets with a remote game API."""
import argparse
import hashlib
from io import BytesIO
from pathlib import Path
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from tools.build_parallel import build_budget, cpu_job, cpu_run, parallel
from tools.package_cache import Inputs, Receipt, digest, runtime_identity
from tools.player_server import player_server
from tools.player_branding import build_icons
from tools.player_assets import website_stadium_preview
from tools.build_tools import BuildError, ffdec_jar, java_binary
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def desktop_client(root, platform, server_url, ffdec=None, java=None):
    """Compile desktop defaults without changing the browser client's SWF."""
    source = (ROOT / 'patches/FlashVarsManager.as').read_text()
    defaults = {
        'server': '1', 'scene3d': '1', 'backend': server_url,
        'clientPlatform': platform, 'clientRuntime': 'flash',
        'clientOS': 'Windows' if platform == 'windows' else 'Linux',
    }
    marker = '         if(param1 == "lang" && this._flashVars.getItem("languageOverride") != "1")'
    if source.count(marker) != 1:
        raise ValueError('FlashVarsManager changed; review desktop defaults injection')
    fallback = ('         if(this._flashVars.getItem(param1) == null)\n'
                '         {\n'
                '            var desktopDefaults:Object = ' + json.dumps(defaults) + ';\n'
                '            if(desktopDefaults.hasOwnProperty(param1)) return String(desktopDefaults[param1]);\n'
                '         }\n')
    source = source.replace(marker, fallback + marker).replace('return "en";', 'return "fr";')
    client = root / 'bin/boufbowl-client-1.9.6.swf'
    ffdec = ffdec_jar(ffdec, download=True)
    java = java_binary(java)
    inputs = Inputs()
    revision = digest({'client': inputs.file(client), 'source': source,
                       'ffdec': inputs.tree(Path(ffdec).parent), 'java': inputs.java(java), 'recipe': 1})
    cache = root / '.local/player-clients' / revision
    output = cache / 'boufbowl-client-1.9.6.swf'
    receipt = Receipt(root, 'desktop-client/'+revision)
    if receipt.current(revision, [output]):
        print('Reusing compiled '+platform+' client', flush=True)
        return output
    cache.mkdir(parents=True, exist_ok=True)
    patch = cache / 'FlashVarsManager.as'
    patch.write_text(source)
    temporary = cache / 'client.building.swf'
    cpu_run([str(java), '-jar', str(Path(ffdec).resolve()), '-replace', str(client), str(temporary),
                    'com.ankamagames.xgaming.utils.flashvars.FlashVarsManager', str(patch)],
                   check=True, timeout=600)
    temporary.replace(output)
    receipt.save(revision, [output])
    return output


def windows_launcher():
    # Local-trusted Flash may read bundled files and connect to the remote API.
    # Delayed expansion preserves spaces and CMD metacharacters in extraction paths.
    return ('@echo off\r\n'
            'setlocal EnableExtensions DisableDelayedExpansion\r\n'
            'set "BOUFBOWL_ROOT=%~dp0"\r\n'
            'set "BOUFBOWL_TRUST=%APPDATA%\\Macromedia\\Flash Player\\#Security\\FlashPlayerTrust"\r\n'
            'setlocal EnableDelayedExpansion\r\n'
            'chcp 65001 >nul 2>&1\r\n'
            'if not exist "!BOUFBOWL_TRUST!" mkdir "!BOUFBOWL_TRUST!"\r\n'
            'if not exist "!BOUFBOWL_TRUST!" goto trust_error\r\n'
            'ver >nul\r\n'
            '> "!BOUFBOWL_TRUST!\\boufbowl-client.cfg" echo(!BOUFBOWL_ROOT!\r\n'
            'if errorlevel 1 goto trust_error\r\n'
            'cd /d "!BOUFBOWL_ROOT!bin"\r\n'
            '"!BOUFBOWL_ROOT!flashplayer.exe" "!BOUFBOWL_ROOT!bin\\boufbowl-client-1.9.6.swf"\r\n'
            'exit /b !errorlevel!\r\n'
            ':trust_error\r\n'
            'echo Impossible de configurer les fichiers locaux de Boufbowl.\r\n'
            'pause\r\n'
            'exit /b 1\r\n')


def windows_executable(archive, makensis=None):
    """Wrap the local Windows payload in a native NSIS launcher."""
    makensis = makensis or shutil.which('makensis')
    if not makensis:
        raise FileNotFoundError('Install NSIS (makensis) or pass --makensis to build the Windows executable')
    icons = build_icons(ROOT, archive.parent/'icons')
    revision = hashlib.sha256(archive.read_bytes()).hexdigest()
    output = archive.with_suffix('.exe')
    temporary = output.with_suffix('.building.exe')
    with tempfile.TemporaryDirectory(prefix='.player-', dir=archive.parent) as directory:
        stage = Path(directory)
        with zipfile.ZipFile(archive) as payload:
            payload.extractall(stage)
        cpu_run([str(makensis), '-V2', '-NOCD',
                        '-DPAYLOAD_DIR=' + str((stage/'Boufbowl').resolve()),
                        '-DBUNDLE_REVISION=' + revision,
                        '-DAPP_ICON=' + str((icons/'icon.ico').resolve()),
                        '-DOUTPUT_FILE=' + str(temporary.resolve()),
                        str(ROOT/'tools/players/windows.nsi')], check=True, timeout=600)
    temporary.replace(output)
    return output


def linux_executable(archive):
    """Append the complete gzip payload to a portable Linux executable script."""
    revision = hashlib.sha256(archive.read_bytes()).hexdigest()
    header = (ROOT/'tools/players/linux.run.sh').read_text().replace('@REVISION@', revision)
    header = header.replace('@PAYLOAD_LINE@', str(header.count('\n') + 1)).encode()
    output = archive.with_name('Boufbowl Fan.run')
    temporary = output.with_suffix('.building.run')
    with temporary.open('wb') as target, archive.open('rb') as source:
        target.write(header)
        shutil.copyfileobj(source, target)
    temporary.chmod(0o755)
    temporary.replace(output)
    return output


def build(root, server_url=None, ffdec=None, java=None, makensis=None, platforms=None):
    root = Path(root)
    selected = tuple(dict.fromkeys(platforms if platforms is not None else ('windows', 'linux')))
    if not selected or any(platform not in ('windows', 'linux') for platform in selected):
        raise ValueError('Select at least one desktop platform: windows or linux')
    server_url = player_server(root, server_url)
    icons = build_icons(root, root/'.local/player-icons')
    player = (root / 'bin/flashplayer_32_sa.exe').read_bytes()
    bundled_files = []
    for folder in ('assets', 'resources'):
        base = root / folder
        if not base.is_dir():
            raise FileNotFoundError(f'Required game files folder is missing: {base}')
        for path in sorted(base.rglob('*')):
            if (path.is_file() and not website_stadium_preview(path)
                    and not (folder == 'assets' and path.is_relative_to(base / 'site'))):
                bundled_files.append((f'Boufbowl/{path.relative_to(root).as_posix()}', path))
    bundled_files.append(('Boufbowl/icon.png', icons/'icon-256.png'))
    readme = (
        'BOUFBOWL FAN — CLIENT DESKTOP\n\n'
        'Le client du jeu et ses assets sont inclus dans les dossiers bin/, assets/ et resources/. '
        'Une connexion Internet reste nécessaire pour rejoindre le serveur du jeu. '
        'Aucun serveur local, Python, Bun ou base de données ne sont nécessaires.\n'
        'Le lanceur configure ce dossier dans FlashPlayerTrust pour autoriser les fichiers '
        'locaux et la connexion au serveur distant.\n\n'
        'Windows : lancer Boufbowl Fan.exe ; les fichiers sont prepares dans LocalAppData.\n'
        'Linux x86-64 : installer Wine avec la prise en charge des applications Windows '
        '32 bits, rendre Boufbowl Fan.run executable puis le lancer. Les fichiers sont '
        'prepares dans le cache utilisateur. Aucun droit administrateur requis.\n\n'
        f'Serveur : {server_url}\n'
    ).encode('utf-8')
    inputs = Inputs()
    common = {'files': {name: inputs.file(path) for name, path in bundled_files},
              'player': inputs.file(root/'bin/flashplayer_32_sa.exe'),
              'readme': hashlib.sha256(readme).hexdigest(), 'server_url': server_url,
              'recipe': inputs.file(Path(__file__)), 'launcher': windows_launcher(), 'runtime': runtime_identity()}
    def package(platform):
        receipt = Receipt(root, 'package-'+platform)
        with receipt.lock():
            return package_locked(platform, receipt)

    def package_locked(platform, receipt):
        client = desktop_client(root, platform, server_url, ffdec=ffdec, java=java)
        folder = root / platform / 'build'
        folder.mkdir(parents=True, exist_ok=True)
        extension = '.zip' if platform == 'windows' else '.tar.gz'
        output = folder/('Boufbowl Fan'+extension)
        executable = folder/('Boufbowl Fan.exe' if platform == 'windows' else 'Boufbowl Fan.run')
        identity = {'common': common, 'platform': platform, 'client': inputs.file(client)}
        if platform == 'windows':
            compiler = makensis or shutil.which('makensis')
            if not compiler:
                raise BuildError('NSIS compiler (makensis) is required for Windows packaging')
            identity.update(icon=inputs.file(icons/'icon.ico'),
                            nsis=inputs.tool(compiler), template=inputs.file(ROOT/'tools/players/windows.nsi'))
            nsis_data = Path(os.environ.get('NSISDIR') or (Path(shutil.which(str(compiler)) or compiler).resolve().parent.parent/'share/nsis'))
            if nsis_data.is_dir():
                identity['nsis_data'] = inputs.tree(nsis_data)
        else:
            identity['template'] = inputs.file(ROOT/'tools/players/linux.run.sh')
        fingerprint = digest(identity)
        if receipt.current(fingerprint, [output, executable]):
            print('Reusing '+platform+' package: '+executable.name, flush=True)
            return executable
        print('Packaging '+platform, flush=True)
        if platform == 'windows':
            output = folder / 'Boufbowl Fan.zip'
            launchers = {'Jouer.cmd': windows_launcher()}
            with cpu_job(), zipfile.ZipFile(output.with_suffix('.building'), 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, content in {'flashplayer.exe': player, **{name: launcher.encode('ascii') for name, launcher in launchers.items()},
                                      'LIRE-MOI.txt': readme}.items():
                    archive.writestr('Boufbowl/' + name, content)
                archive.write(client, 'Boufbowl/bin/boufbowl-client-1.9.6.swf')
                for name, path in bundled_files:
                    archive.write(path, name)
        else:
            output = folder / 'Boufbowl Fan.tar.gz'
            launcher = '#!/bin/sh\nset -eu\ncd -- "$(dirname -- "$0")"\n'
            launcher += 'if ! command -v wine >/dev/null 2>&1; then\n  echo "Installez Wine avec la prise en charge 32 bits pour jouer." >&2\n  exit 1\nfi\n'
            launcher += 'exec wine cmd /d /c Jouer.cmd\n'
            with cpu_job(), tarfile.open(output.with_suffix('.building'), 'w:gz') as archive:
                for name, content in {'flashplayer.exe': player, 'Jouer.cmd': windows_launcher().encode('ascii'), 'jouer.sh': launcher.encode(), 'LIRE-MOI.txt': readme}.items():
                    info = tarfile.TarInfo('Boufbowl/' + name)
                    info.size = len(content)
                    info.mode = 0o755 if name.endswith(('.sh', '.exe')) else 0o644
                    archive.addfile(info, BytesIO(content))
                archive.add(client, 'Boufbowl/bin/boufbowl-client-1.9.6.swf')
                for name, path in bundled_files:
                    archive.add(path, name)
        output.with_suffix('.building').replace(output)
        executable = windows_executable(output, makensis) if platform == 'windows' else linux_executable(output)
        receipt.save(fingerprint, [output, executable])
        return executable
    outputs = dict(parallel(lambda platform: (platform, package(platform)), selected))
    return [outputs[platform] for platform in selected]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', '--platforms', action='extend', nargs='+', choices=('windows', 'linux'),
                        help='Platforms to build (default: windows linux; repeatable)')
    parser.add_argument('--jobs', type=int, help='Maximum concurrent CPU jobs (default: available CPUs)')
    parser.add_argument('--server-url', help='Override resources/site.json hosted server')
    parser.add_argument('--ffdec', type=Path, help='Path to ffdec.jar (or set FFDEC_JAR)')
    parser.add_argument('--java', help='Java executable (default: java on PATH)')
    parser.add_argument('--makensis', help='NSIS compiler executable (default: makensis on PATH)')
    parser.add_argument('--bun', default='bun', help='Bun executable for refreshing the website')
    parser.add_argument('--no-website', action='store_true', help='Build bundles only; defer website generation')
    args = parser.parse_args()
    if args.jobs is not None and args.jobs < 1:
        parser.error('--jobs must be positive')
    with build_budget(args.jobs):
        for output in build(ROOT, args.server_url, ffdec=args.ffdec, java=args.java, makensis=args.makensis, platforms=args.platform):
            print(f'Built {output} ({output.stat().st_size} bytes)', flush=True)
        if not args.no_website:
            from tools.refresh_website import refresh_website
            refresh_website(ROOT, args.bun)


if __name__ == '__main__':
    import sys
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(f'Desktop build stopped: {Path(str(error.cmd[0])).name} exited with code {error.returncode}. See the error above.', file=sys.stderr)
        sys.exit(1)
    except (BuildError, OSError, ValueError) as error:
        print(f'Desktop build stopped: {error}', file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('Desktop build interrupted.', file=sys.stderr)
        sys.exit(130)
