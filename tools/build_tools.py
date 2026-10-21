"""Resolve shared build tools and fetch the pinned FFDec release when needed."""
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import urllib.request
import zipfile

FFDEC_VERSION = '26.3.0'
FFDEC_URL = f'https://github.com/jindrapetrik/jpexs-decompiler/releases/download/version{FFDEC_VERSION}/ffdec_{FFDEC_VERSION}.zip'
FFDEC_SHA256 = '35f4930eb7c380afe66f2117f90b006deac0631473ad7500bb39c78f68645ecd'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', Path.home()/'.cache'))/'boufbowl-flash-tools'


class BuildError(RuntimeError):
    pass


def ffdec_jar(explicit=None, download=False):
    value = str(explicit or '').strip() or os.environ.get('FFDEC_JAR', '').strip()
    if value:
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            raise BuildError(f'FFDec must point to a JAR file, not {path}. Unset FFDEC_JAR to use automatic setup.')
        return path
    candidates = [CACHE/f'ffdec-{FFDEC_VERSION}/ffdec.jar', CACHE/'ffdec/ffdec.jar',
                  CACHE/'ffdec/ffdec-cli.jar', Path('/usr/share/java/ffdec/ffdec.jar'),
                  Path('/usr/share/ffdec/ffdec.jar'), Path('/opt/ffdec/ffdec.jar')]
    found = next((path for path in candidates if path.is_file()), None)
    if found:
        return found.resolve()
    if not download:
        raise BuildError('FFDec is missing. Run bun run build to download and configure it automatically.')
    CACHE.mkdir(parents=True, exist_ok=True)
    print(f'Downloading FFDec {FFDEC_VERSION} (about 20 MB)…', flush=True)
    with tempfile.TemporaryDirectory(prefix='.ffdec-', dir=CACHE) as temporary:
        temporary = Path(temporary)
        archive = temporary/'ffdec.zip'
        request = urllib.request.Request(FFDEC_URL, headers={'User-Agent': 'Boufbowl-build'})
        with urllib.request.urlopen(request, timeout=60) as response, archive.open('wb') as target:
            shutil.copyfileobj(response, target)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != FFDEC_SHA256:
            raise BuildError('FFDec download checksum mismatch; refusing to install it. Retry the build.')
        extracted = temporary/'files'
        extracted.mkdir()
        with zipfile.ZipFile(archive) as bundle:
            for entry in bundle.infolist():
                if (not (extracted/entry.filename).resolve().is_relative_to(extracted.resolve())
                        or stat.S_ISLNK(entry.external_attr >> 16)):
                    raise BuildError('Unsafe entry in FFDec archive')
            bundle.extractall(extracted)
        if not (extracted/'ffdec.jar').is_file():
            raise BuildError('FFDec archive has no ffdec.jar')
        shutil.copytree(extracted, CACHE/f'ffdec-{FFDEC_VERSION}', dirs_exist_ok=True)
    return (CACHE/f'ffdec-{FFDEC_VERSION}/ffdec.jar').resolve()


def java_binary(explicit=None):
    candidates = [explicit, os.environ.get('JAVA'),
                  str(Path(os.environ['JAVA_HOME'])/'bin/java') if os.environ.get('JAVA_HOME') else None,
                  shutil.which('java'), *sorted(CACHE.glob('jdk-17/*/bin/java')),
                  '/usr/lib/jvm/java-17-openjdk/bin/java', '/usr/lib/jvm/java-17-openjdk-amd64/bin/java',
                  '/usr/lib/jvm/java-17-openjdk-arm64/bin/java']
    for candidate in candidates:
        if not candidate:
            continue
        resolved = shutil.which(str(candidate))
        if not resolved:
            continue
        result = subprocess.run([resolved, '-version'], capture_output=True, text=True)
        match = re.search(r'version "(\d+)', result.stderr + result.stdout)
        if result.returncode == 0 and match and int(match[1]) >= 17:
            return Path(resolved).resolve()
    raise BuildError('Java 17+ is missing. Ubuntu/Debian: sudo apt install openjdk-17-jre-headless. Arch: sudo pacman -S jre17-openjdk.')
