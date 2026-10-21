"""Content fingerprints and verified receipts for incremental player packages."""
from contextlib import contextmanager
import hashlib
import json
import os
import platform
import sys
import zlib
from pathlib import Path
import shutil
import stat
import threading


def runtime_identity():
    return {'python': sys.version, 'zlib': zlib.ZLIB_RUNTIME_VERSION,
            'os': platform.system(), 'machine': platform.machine()}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def files_in(directory, ancestors=frozenset()):
    """Include linked tool directories, but stop symlink cycles."""
    directory = Path(directory)
    if not directory.exists():
        return
    info = directory.stat()
    identity = (info.st_dev, info.st_ino)
    if identity in ancestors:
        return
    ancestors = ancestors | {identity}
    for path in sorted(directory.iterdir()):
        if path.is_file():
            yield path
        elif path.is_dir():
            yield from files_in(path, ancestors)


class Inputs:
    """Read each shared input once per invocation, without trusting timestamps."""
    def __init__(self):
        self._files = {}
        self._lock = threading.Lock()

    def file(self, filename):
        path = Path(filename)
        key = str(path.absolute())
        with self._lock:
            if key not in self._files:
                with path.open('rb') as source:
                    sha = hashlib.file_digest(source, 'sha256').hexdigest()
                info = path.stat()
                self._files[key] = {'sha256': sha, 'size': info.st_size, 'mode': stat.S_IMODE(info.st_mode)}
            return self._files[key]

    def tree(self, directory):
        directory = Path(directory)
        return {path.relative_to(directory).as_posix(): self.file(path)
                for path in files_in(directory)}

    def tool(self, executable):
        path = Path(shutil.which(str(executable)) or executable).resolve()
        return {'binary': self.file(path)}

    def java(self, executable):
        path = Path(executable).resolve()
        root = path.parent.parent
        return {'java': self.file(path),
                'release': self.file(root/'release') if (root/'release').is_file() else None,
                'modules': self.file(root/'lib/modules') if (root/'lib/modules').is_file() else None,
                'vm': {p.relative_to(root).as_posix(): self.file(p)
                       for p in sorted((root/'lib').glob('**/libjvm.*')) if p.is_file()}}


class Receipt:
    def __init__(self, root, name):
        self.root = Path(root)
        self.path = self.root/'.local/player-builds'/f'{name}.json'

    def current(self, fingerprint, outputs):
        try:
            saved = json.loads(self.path.read_text())
            return (isinstance(saved, dict) and saved.get('input') == fingerprint
                    and saved.get('outputs') == self._outputs(outputs))
        except (OSError, ValueError):
            return False

    def _outputs(self, outputs):
        paths = list(outputs)
        if not paths:
            raise ValueError('A build receipt needs at least one output')
        inputs = Inputs()
        return {Path(path).relative_to(self.root).as_posix(): inputs.file(path) for path in paths}

    def save(self, fingerprint, outputs):
        value = {'version': 1, 'input': fingerprint, 'outputs': self._outputs(outputs)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.building.json')
        temporary.write_text(json.dumps(value, indent=2)+'\n')
        temporary.replace(self.path)

    @contextmanager
    def lock(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_suffix('.lock').open('a+b') as handle:
            if os.name == 'nt':
                import msvcrt
                handle.seek(0)
                if not handle.read(1):
                    handle.write(b'0')
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == 'nt':
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def copy_changed(source, target):
    source, target = Path(source), Path(target)
    if target.is_file() and Inputs().file(source) == Inputs().file(target):
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name('.'+target.name+'.copying')
    shutil.copy2(source, temporary)
    temporary.replace(target)
    return True


def sync_tree(source, target, include=lambda path: True, preserve=()):
    """Copy changed inputs and delete obsolete files, retaining known generated files."""
    source, target = Path(source), Path(target)
    expected = {path.relative_to(source): path for path in source.rglob('*') if path.is_file() and include(path)}
    keep = set(expected) | {Path(path) for path in preserve}
    copied = sum(copy_changed(path, target/relative) for relative, path in expected.items())
    removed = 0
    if target.exists():
        for path in target.rglob('*'):
            if path.is_file() and path.relative_to(target) not in keep:
                path.unlink()
                removed += 1
        for path in sorted(target.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
    target.mkdir(parents=True, exist_ok=True)
    return {'copied': copied, 'removed': removed, 'reused': len(expected)-copied}
