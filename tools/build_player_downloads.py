"""Package remote-only Windows and Linux players, without a local server."""
import argparse
import hashlib
from io import BytesIO
from pathlib import Path
import shlex
import tarfile
from urllib.parse import urlencode, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def build(root, server_url):
    root = Path(root)
    endpoint = urlsplit(server_url)
    if (endpoint.scheme != 'https' or not endpoint.hostname or endpoint.username
            or endpoint.password or endpoint.query or endpoint.fragment):
        raise ValueError('Use an HTTPS server URL without credentials, query or fragment')
    server_url = server_url.rstrip('/')
    player = (root / 'bin/flashplayer_32_sa.exe').read_bytes()
    revision = hashlib.sha256((root / 'bin/boufbowl-client-1.9.6.swf').read_bytes()).hexdigest()
    readme = (
        'BOUFBOWL — CLIENT EN LIGNE\n\n'
        'Une connexion Internet est nécessaire. Le jeu et ses ressources sont chargés '
        'depuis le serveur distant ; aucun serveur local, Python, Bun ou base de données '
        'ne sont nécessaires sur votre ordinateur.\n\n'
        'Windows : extraire le ZIP puis double-cliquer sur Jouer.cmd. Wine est inutile.\n'
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
            launcher = '@echo off\r\nstart "" "%~dp0flashplayer.exe" "' + url.replace('%', '%%') + '"\r\n'
            with zipfile.ZipFile(output.with_suffix('.building'), 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, content in {'flashplayer.exe': player, 'Jouer.cmd': launcher.encode('ascii'), 'LIRE-MOI.txt': readme}.items():
                    archive.writestr('Boufbowl/' + name, content)
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
        output.with_suffix('.building').replace(output)
        outputs.append(output)
    return outputs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-url', required=True)
    args = parser.parse_args()
    for output in build(ROOT, args.server_url):
        print(f'Built {output} ({output.stat().st_size} bytes)')
