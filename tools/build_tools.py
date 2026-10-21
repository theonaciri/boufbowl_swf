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


def _java_major(executable):
    try:
        result = subprocess.run([str(executable), '-version'], capture_output=True, text=True, timeout=15)
        match = re.search(r'version "(\d+)', result.stderr + result.stdout)
        return int(match[1]) if result.returncode == 0 and match else 0
    except (OSError, subprocess.TimeoutExpired):
        return 0


def java_binary(explicit=None):
    saved = _saved_tool('JDK')
    executable = 'java.exe' if os.name == 'nt' else 'java'
    candidates = [explicit, os.environ.get('JAVA'),
                  str(Path(os.environ['JDK_HOME'])/'bin'/executable) if os.environ.get('JDK_HOME') else None,
                  str(Path(os.environ['JAVA_HOME'])/'bin'/executable) if os.environ.get('JAVA_HOME') else None,
                  str(Path(saved)/'bin'/executable) if saved else None,
                  shutil.which('java'), *sorted(CACHE.glob('jdk-*/**/bin/'+executable), key=_version_key, reverse=True),
                  '/usr/lib/jvm/java-17-openjdk/bin/java', '/usr/lib/jvm/java-17-openjdk-amd64/bin/java',
                  '/usr/lib/jvm/java-17-openjdk-arm64/bin/java']
    visited = set()
    for candidate in candidates:
        if not candidate:
            continue
        resolved = shutil.which(str(candidate))
        if not resolved or resolved in visited:
            continue
        visited.add(resolved)
        if _java_major(resolved) >= 17:
            return Path(resolved).resolve()
    for directory in _search_jdks():
        if _valid_jdk(directory):
            directory = directory.resolve()
            remember_build_tools(JDK=directory)
            return directory/'bin'/executable
    raise BuildError('Java 17+ was not found, including the recursive JDK search. Ubuntu/Debian: sudo apt install openjdk-17-jdk-headless. Arch: sudo pacman -S jdk17-openjdk.')


def _version_key(path):
    return tuple((1, int(part)) if part.isdigit() else (0, part.lower())
                 for part in re.split(r'(\d+)', str(path)))


def _saved_tool(name):
    import json
    try:
        saved = json.loads((Path(__file__).resolve().parent.parent/'.local/build-tools.json').read_text())
        return saved.get(name) if isinstance(saved, dict) else None
    except (OSError, ValueError):
        return None


def _find_sdk(name, explicit, environment, candidates, valid, hint, search=None):
    # A supplied override must be valid; stale automatically saved paths can fall back.
    override = explicit or next((os.environ[key] for key in environment if os.environ.get(key)), None)
    if override:
        path = Path(override).expanduser().resolve()
        if not valid(path):
            raise BuildError(f'{name} is incomplete or missing at {path}. {hint}')
        return path
    for candidate in [_saved_tool(name), *candidates]:
        if candidate:
            path = Path(candidate).expanduser().resolve()
            if valid(path):
                return path
    if search:
        for candidate in search():
            path = Path(candidate).resolve()
            if valid(path):
                remember_build_tools(**{name: path})
                return path
    locations = 'the project, tool cache, or standard installation folders'
    if search:
        locations += ' or the recursive installation search'
    raise BuildError(f'{name} was not found in {locations}. {hint}')


def _search_installations(label, marker, extra_roots=()):
    """Find extracted toolchains even when parent folders have arbitrary names."""
    root = Path(__file__).resolve().parent.parent
    roots = [root, CACHE, Path.home(), *map(Path, extra_roots),
             Path('/opt'), Path('/usr/local'), Path('/usr/share')]
    print(f'Searching recursively for {label} ({marker}) in the project, home directory and installation folders…', flush=True)
    marker = Path(marker)
    visited = set()
    skipped = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', '.Trash', 'Trash'}
    for base in roots:
        if not base.is_dir():
            continue
        # Do not follow directory symlinks recursively: they may lead back to a
        # parent or into unrelated filesystem trees. Direct SDK links still work.
        for directory, children, files in os.walk(base, followlinks=False):
            path = Path(directory)
            try:
                info = path.stat()
            except OSError:
                children[:] = []
                continue
            identity = (info.st_dev, info.st_ino)
            if identity in visited:
                children[:] = []
                continue
            visited.add(identity)
            if path.name == marker.parent.name and marker.name in files:
                yield path.parent
            children[:] = sorted((name for name in children if name not in skipped),
                                 key=_version_key, reverse=True)
            for child in children:
                candidate = path/child
                if candidate.is_symlink() and (candidate/marker).is_file():
                    yield candidate



def _search_air_sdks():
    yield from _search_installations('AIR SDK', 'lib/adt.jar')


def _search_jdks():
    compiler = 'javac.exe' if os.name == 'nt' else 'javac'
    yield from _search_installations('JDK 17+', 'bin/'+compiler,
                                     ('/usr/lib/jvm', '/usr/java', '/Library/Java/JavaVirtualMachines'))


def _valid_jdk(path):
    executable = 'java.exe' if os.name == 'nt' else 'java'
    compiler = 'javac.exe' if os.name == 'nt' else 'javac'
    return ((path/'bin'/compiler).is_file() and (path/'bin'/executable).is_file()
            and _java_major(path/'bin'/executable) >= 17)


def air_sdk(explicit=None):
    root = Path(__file__).resolve().parent.parent
    candidates = [
        *sorted(CACHE.glob('air-sdk*'), key=_version_key, reverse=True), CACHE/'AIRSDK',
        *sorted(Path('/opt').glob('air-sdk*'), key=_version_key, reverse=True),
        *sorted((root/'.local').glob('air-sdk*'), key=_version_key, reverse=True),
        root/'.local/AIRSDK', root/'.local/air-sdk', root/'.local/tools/AIRSDK',
        root/'AIRSDK', root/'air-sdk',
        Path.home()/'AIRSDK', Path.home()/'air-sdk', Path.home()/'SDKs/AIRSDK',
        Path.home()/'sdk/AIRSDK', Path.home()/'.local/share/AIRSDK',
        '/opt/AIRSDK', '/opt/air-sdk', '/opt/airsdk', '/usr/local/lib/airsdk', '/usr/share/airsdk',
    ]
    adt = shutil.which('adt')
    if adt:
        candidates.insert(0, Path(adt).resolve().parent.parent)
    return _find_sdk('AIR SDK', explicit, ('AIR_SDK', 'AIRSDK_HOME', 'AIR_HOME'), candidates,
                     lambda path: (path/'lib/adt.jar').is_file(),
                     f'Install/extract the AIR SDK into {CACHE}/air-sdk and rerun; installed SDKs are found and remembered automatically.',
                     search=_search_air_sdks)


def android_sdk(explicit=None):
    root = Path(__file__).resolve().parent.parent
    candidates = [
        CACHE/'android-sdk', root/'.local/android-sdk',
        Path.home()/'Android/Sdk', Path.home()/'Android/sdk',
        Path.home()/'.android/sdk', Path.home()/'Library/Android/sdk',
        '/opt/android-sdk', '/opt/android-sdk-linux', '/usr/lib/android-sdk', '/usr/share/android-sdk',
    ]
    sdkmanager = shutil.which('sdkmanager')
    if sdkmanager:
        candidates = [*Path(sdkmanager).resolve().parents, *candidates]
    return _find_sdk('Android SDK', explicit, ('ANDROID_HOME', 'ANDROID_SDK_ROOT'), candidates,
                     lambda path: (path/'platforms').is_dir() and (path/'build-tools').is_dir(),
                     'Install Android SDK platforms and build tools, or pass --android-sdk /path/to/Android/Sdk once; the path is remembered.')


def jdk_directory(explicit=None):
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not _valid_jdk(path):
            raise BuildError(f'A full JDK 17+ is required at {path}; pass --jdk /path/to/jdk-17.')
        return path
    executable = 'java.exe' if os.name == 'nt' else 'java'
    candidates = [_saved_tool('JDK'), os.environ.get('JDK_HOME'), os.environ.get('JAVA_HOME')]
    javac = shutil.which('javac')
    if javac:
        candidates.append(Path(javac).resolve().parent.parent)
    candidates += [*sorted(CACHE.glob('jdk-*/*'), key=_version_key, reverse=True),
                   *sorted(CACHE.glob('jdk-*'), key=_version_key, reverse=True),
                   *sorted(Path('/usr/lib/jvm').glob('*'), key=_version_key, reverse=True)]
    java = shutil.which(executable)
    if java:
        candidates.append(Path(java).resolve().parent.parent)
    visited = set()
    for candidate in candidates:
        if candidate:
            path = Path(candidate).expanduser().resolve()
            if path not in visited:
                visited.add(path)
                if _valid_jdk(path):
                    return path
    for candidate in _search_jdks():
        path = candidate.resolve()
        if path not in visited:
            visited.add(path)
            if _valid_jdk(path):
                remember_build_tools(JDK=path)
                return path
    raise BuildError('A full JDK 17+ was not found, including the recursive installation search. Ubuntu/Debian: sudo apt install openjdk-17-jdk-headless. Or pass --jdk /path/to/jdk-17.')


def remember_build_tools(**paths):
    import json
    destination = Path(__file__).resolve().parent.parent/'.local/build-tools.json'
    try:
        saved = json.loads(destination.read_text())
        if not isinstance(saved, dict):
            saved = {}
    except (OSError, ValueError):
        saved = {}
    saved.update({key: str(Path(value).resolve()) for key, value in paths.items()})
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix('.building.json')
    temporary.write_text(json.dumps(saved, indent=2)+'\n')
    temporary.replace(destination)
