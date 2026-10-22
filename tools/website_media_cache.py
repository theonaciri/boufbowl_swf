"""Track media inputs separately so ordinary website builds reuse finished exports."""
import hashlib
import json
from pathlib import Path


class MediaCache:
    def __init__(self, root):
        self.root = Path(root)
        self.path = self.root/'.local/website/media-stages.json'
        try:
            saved = json.loads(self.path.read_text())
            self.stages = saved if isinstance(saved, dict) else {}
        except (OSError, ValueError):
            self.stages = {}
        self.hashes = {}

    def files(self, patterns):
        return sorted({path for pattern in patterns for path in self.root.glob(pattern) if path.is_file()})

    def fingerprint(self, patterns):
        rows = []
        for path in self.files(patterns):
            if path not in self.hashes:
                self.hashes[path] = hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append((path.relative_to(self.root).as_posix(), self.hashes[path]))
        return hashlib.sha256(json.dumps([1, patterns, rows], sort_keys=True).encode()).hexdigest()

    def outputs(self, patterns):
        return {path.relative_to(self.root).as_posix(): {'bytes': path.stat().st_size, 'sha256': self.file_hash(path)}
                for path in self.files(patterns)}

    @staticmethod
    def file_hash(path):
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(chunk)
        return digest.hexdigest()

    def current(self, name, inputs, outputs):
        return self.reason(name, inputs, outputs) is None

    def reason(self, name, inputs, outputs):
        entry = self.stages.get(name)
        if not isinstance(entry, dict):
            return 'no completed build record'
        if entry.get('inputs') != self.fingerprint(inputs):
            return 'media inputs or generator changed'
        actual = self.outputs(outputs)
        if not actual:
            return 'generated media missing'
        saved = entry.get('outputs')
        if saved == actual:
            return None
        # Upgrade an intact timestamp-based receipt without regenerating media.
        legacy = {path.relative_to(self.root).as_posix(): [path.stat().st_size, path.stat().st_mtime_ns]
                  for path in self.files(outputs)}
        if saved == legacy:
            entry['outputs'] = actual
            self.write()
            return None
        return 'generated media changed or missing'

    def save(self, name, inputs, outputs):
        self.stages[name] = {'inputs': self.fingerprint(inputs), 'outputs': self.outputs(outputs)}
        self.write()

    def write(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.building.json')
        temporary.write_text(json.dumps(self.stages, indent=2)+'\n')
        temporary.replace(self.path)
