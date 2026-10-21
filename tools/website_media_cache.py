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
        return {path.relative_to(self.root).as_posix(): [path.stat().st_size, path.stat().st_mtime_ns]
                for path in self.files(patterns)}

    def current(self, name, inputs, outputs):
        entry = self.stages.get(name, {})
        if not isinstance(entry, dict):
            return False
        actual = self.outputs(outputs)
        return bool(actual) and entry.get('inputs') == self.fingerprint(inputs) and entry.get('outputs') == actual

    def save(self, name, inputs, outputs):
        self.stages[name] = {'inputs': self.fingerprint(inputs), 'outputs': self.outputs(outputs)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.building.json')
        temporary.write_text(json.dumps(self.stages, indent=2)+'\n')
        temporary.replace(self.path)
