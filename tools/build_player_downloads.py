"""Package remote-only Windows and Linux players, without a local server."""
import argparse
import hashlib
from io import BytesIO
from pathlib import Path
import shlex
import tarfile
from urllib.parse import urlencode
from tools.player_server import player_server
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def build(root, server_url=None):
    root = Path(root)
    server_url = player_server(root, server_url)
    player = (root / 'bin/flashplayer_32_sa.exe').read_bytes()
    revision = hashlib.sha256((root / 'bin/boufbowl-client-1.9.6.swf').read_bytes()).hexdigest()
    bundled_files = []
    for folder in ('assets', 'resources'):
        base = root / folder
        if not base.is_dir():
            raise FileNotFoundError(f'Required game files folder is missing: {base}')
        for path in sorted(base.rglob('*')):
            if path.is_file() and not (folder == 'assets' and path.is_relative_to(base / 'site')):
                bundled_files.append((f'Boufbowl/{path.relative_to(root).as_posix()}', path))
    readme = (
        'BOUFBOWL — CLIENT DESKTOP\n\n'
        'Les assets du jeu sont inclus dans les dossiers assets/ et resources/. '
        'Une connexion Internet reste nécessaire pour rejoindre le serveur du jeu. '
        'Aucun serveur local, Python, Bun ou base de données ne sont nécessaires.\n\n'
        'Windows : extraire le ZIP puis lancer Jouer.cmd. Wine est inutile.\n'
        'Linux x86-64 : installer Wine avec la prise en charge des applications Windows '
        '32 bits, extraire l’archive puis lancer ./jouer.sh.\n\n'
        f'Serveur : {server_url}\n'
    ).encode('utf-8')
    outputs = []
    for platform in ('windows', 'linux'):
        url = server_url + '/bin/boufbowl-client-1.9.6.swf?' + urlencode({
            'lang': 'fr', 'server': '1', 'scene3d': '1', 'backend': server_url,
            'clientPlatform': platform, 'clientRuntime': 'flash',
            'clientOS': 'Windows' if platform == 'windows' else 'Linux', 'v': revision,
        })
        folder = root / platform / 'build'
        folder.mkdir(parents=True, exist_ok=True)
        if platform == 'windows':
            output = folder / 'Boufbowl-windows.zip'
            escaped_url = url.replace('%', '%%')
            def windows_launcher(*flags):
                suffix = ''.join('&' + flag + '=1' for flag in flags)
                return '@echo off\r\nstart "" "%~dp0flashplayer.exe" "' + escaped_url + suffix + '"\r\n'
            launchers = {
                'Jouer.cmd': windows_launcher(),
            }
            with zipfile.ZipFile(output.with_suffix('.building'), 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, content in {'flashplayer.exe': player, **{name: launcher.encode('ascii') for name, launcher in launchers.items()},
                                      'LIRE-MOI.txt': readme}.items():
                    archive.writestr('Boufbowl/' + name, content)
                for name, path in bundled_files:
                    archive.write(path, name)
        else:
            output = folder / 'Boufbowl-linux.tar.gz'
            launcher = '#!/bin/sh\nset -eu\ncd -- "$(dirname -- "$0")"\n'
            launcher += 'if ! command -v wine >/dev/null 2>&1; then\n  echo "Installez Wine avec la prise en charge 32 bits pour jouer." >&2\n  exit 1\nfi\n'
            launcher += 'exec wine ./flashplayer.exe ' + shlex.quote(url) + '\n'
            with tarfile.open(output.with_suffix('.building'), 'w:gz') as archive:
                for name, content in {'flashplayer.exe': player, 'jouer.sh': launcher.encode(), 'LIRE-MOI.txt': readme}.items():
                    info = tarfile.TarInfo('Boufbowl/' + name)
                    info.size = len(content)
                    info.mode = 0o755 if name.endswith(('.sh', '.exe')) else 0o644
                    archive.addfile(info, BytesIO(content))
                for name, path in bundled_files:
                    archive.add(path, name)
        output.with_suffix('.building').replace(output)
        outputs.append(output)
    return outputs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-url', help='Override resources/site.json hosted server')
    args = parser.parse_args()
    for output in build(ROOT, args.server_url):
        print(f'Built {output} ({output.stat().st_size} bytes)')
