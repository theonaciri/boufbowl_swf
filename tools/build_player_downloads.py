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
from tools.player_server import player_server
from tools.player_assets import website_stadium_preview
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
    revision = hashlib.sha256(client.read_bytes() + source.encode()).hexdigest()
    cache = root / '.local/player-clients' / revision
    output = cache / 'boufbowl-client-1.9.6.swf'
    if output.is_file():
        return output
    cache.mkdir(parents=True, exist_ok=True)
    patch = cache / 'FlashVarsManager.as'
    patch.write_text(source)
    cache_root = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache'))
    ffdec = ffdec or os.environ.get('FFDEC_JAR')
    if not ffdec:
        ffdec = next((candidate for candidate in (
            cache_root / 'boufbowl-flash-tools/ffdec-26.3.0/ffdec.jar',
            cache_root / 'boufbowl-flash-tools/ffdec/ffdec.jar',
        ) if candidate.is_file()), None)
    if not ffdec or not Path(ffdec).is_file():
        raise FileNotFoundError('Set FFDEC_JAR or pass --ffdec to compile the bundled desktop clients')
    java = java or shutil.which('java')
    if not java:
        raise FileNotFoundError('Put Java on PATH or pass --java to compile the bundled desktop clients')
    temporary = cache / 'client.building.swf'
    subprocess.run([str(java), '-jar', str(Path(ffdec).resolve()), '-replace', str(client), str(temporary),
                    'com.ankamagames.xgaming.utils.flashvars.FlashVarsManager', str(patch)],
                   check=True, timeout=600)
    temporary.replace(output)
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
    revision = hashlib.sha256(archive.read_bytes()).hexdigest()
    output = archive.with_suffix('.exe')
    temporary = output.with_suffix('.building.exe')
    with tempfile.TemporaryDirectory(prefix='.player-', dir=archive.parent) as directory:
        stage = Path(directory)
        with zipfile.ZipFile(archive) as payload:
            payload.extractall(stage)
        subprocess.run([str(makensis), '-V2', '-NOCD',
                        '-DPAYLOAD_DIR=' + str((stage/'Boufbowl').resolve()),
                        '-DBUNDLE_REVISION=' + revision,
                        '-DOUTPUT_FILE=' + str(temporary.resolve()),
                        str(ROOT/'tools/players/windows.nsi')], check=True, timeout=600)
    temporary.replace(output)
    return output


def linux_executable(archive):
    """Append the complete gzip payload to a portable Linux executable script."""
    revision = hashlib.sha256(archive.read_bytes()).hexdigest()
    header = (ROOT/'tools/players/linux.run.sh').read_text().replace('@REVISION@', revision)
    header = header.replace('@PAYLOAD_LINE@', str(header.count('\n') + 1)).encode()
    output = archive.with_name('Boufbowl-linux.run')
    temporary = output.with_suffix('.building.run')
    with temporary.open('wb') as target, archive.open('rb') as source:
        target.write(header)
        shutil.copyfileobj(source, target)
    temporary.chmod(0o755)
    temporary.replace(output)
    return output


def build(root, server_url=None, ffdec=None, java=None, makensis=None):
    root = Path(root)
    server_url = player_server(root, server_url)
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
    readme = (
        'BOUFBOWL — CLIENT DESKTOP\n\n'
        'Le client du jeu et ses assets sont inclus dans les dossiers bin/, assets/ et resources/. '
        'Une connexion Internet reste nécessaire pour rejoindre le serveur du jeu. '
        'Aucun serveur local, Python, Bun ou base de données ne sont nécessaires.\n'
        'Le lanceur configure ce dossier dans FlashPlayerTrust pour autoriser les fichiers '
        'locaux et la connexion au serveur distant.\n\n'
        'Windows : lancer Boufbowl-windows.exe ; les fichiers sont prepares dans LocalAppData.\n'
        'Linux x86-64 : installer Wine avec la prise en charge des applications Windows '
        '32 bits, rendre Boufbowl-linux.run executable puis le lancer. Les fichiers sont '
        'prepares dans le cache utilisateur. Aucun droit administrateur requis.\n\n'
        f'Serveur : {server_url}\n'
    ).encode('utf-8')
    outputs = []
    for platform in ('windows', 'linux'):
        client = desktop_client(root, platform, server_url, ffdec=ffdec, java=java)
        folder = root / platform / 'build'
        folder.mkdir(parents=True, exist_ok=True)
        if platform == 'windows':
            output = folder / 'Boufbowl-windows.zip'
            launchers = {'Jouer.cmd': windows_launcher()}
            with zipfile.ZipFile(output.with_suffix('.building'), 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, content in {'flashplayer.exe': player, **{name: launcher.encode('ascii') for name, launcher in launchers.items()},
                                      'LIRE-MOI.txt': readme}.items():
                    archive.writestr('Boufbowl/' + name, content)
                archive.write(client, 'Boufbowl/bin/boufbowl-client-1.9.6.swf')
                for name, path in bundled_files:
                    archive.write(path, name)
        else:
            output = folder / 'Boufbowl-linux.tar.gz'
            launcher = '#!/bin/sh\nset -eu\ncd -- "$(dirname -- "$0")"\n'
            launcher += 'if ! command -v wine >/dev/null 2>&1; then\n  echo "Installez Wine avec la prise en charge 32 bits pour jouer." >&2\n  exit 1\nfi\n'
            launcher += 'exec wine cmd /d /c Jouer.cmd\n'
            with tarfile.open(output.with_suffix('.building'), 'w:gz') as archive:
                for name, content in {'flashplayer.exe': player, 'Jouer.cmd': windows_launcher().encode('ascii'), 'jouer.sh': launcher.encode(), 'LIRE-MOI.txt': readme}.items():
                    info = tarfile.TarInfo('Boufbowl/' + name)
                    info.size = len(content)
                    info.mode = 0o755 if name.endswith(('.sh', '.exe')) else 0o644
                    archive.addfile(info, BytesIO(content))
                archive.add(client, 'Boufbowl/bin/boufbowl-client-1.9.6.swf')
                for name, path in bundled_files:
                    archive.add(path, name)
        output.with_suffix('.building').replace(output)
        outputs.append(windows_executable(output, makensis) if platform == 'windows' else linux_executable(output))
    return outputs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-url', help='Override resources/site.json hosted server')
    parser.add_argument('--ffdec', type=Path, help='Path to ffdec.jar (or set FFDEC_JAR)')
    parser.add_argument('--java', help='Java executable (default: java on PATH)')
    parser.add_argument('--makensis', help='NSIS compiler executable (default: makensis on PATH)')
    parser.add_argument('--bun', default='bun', help='Bun executable for refreshing the website')
    parser.add_argument('--no-website', action='store_true', help='Build bundles only; defer website generation')
    args = parser.parse_args()
    for output in build(ROOT, args.server_url, ffdec=args.ffdec, java=args.java, makensis=args.makensis):
        print(f'Built {output} ({output.stat().st_size} bytes)', flush=True)
    if not args.no_website:
        from tools.refresh_website import refresh_website
        refresh_website(ROOT, args.bun)
