"""Shared renderer dependencies, excluding colors supplied explicitly per task."""
import hashlib
import json
from pathlib import Path

CLIENT = 'bin/boufbowl-client-1.9.6.swf'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def logic_fingerprint(root, original=None, config=None):
    paths = set()
    for pattern in ('patches/*.as', 'patches/*.inc', 'tools/*codegen.py',
                    'tools/game_config.py', 'tools/visual_assets.py',
                    'tools/media_fingerprints.py', 'tools/client_patches.py', 'patches/rebuild.py',
                    'resources/local_ui.json', 'resources/cosmetic_catalog.json', 'resources/release.json', 'resources/site.json'):
        paths.update(p for p in root.glob(pattern) if p.is_file())
    rows = {p.relative_to(root).as_posix(): file_hash(p) for p in sorted(paths)}
    rows['base'] = file_hash(original or root/'bin/base/boufbowl-client-1.9.6.swf')
    rows['config'] = file_hash(config or root/'resources/game_config.json')
    return digest(rows)


def client_fingerprint(root):
    actual = file_hash(root/CLIENT)
    receipt = read_json(root/'.local/game-build.json', {})
    if receipt.get('client') == actual:
        return receipt['logic']
    # Unrecognized clients cannot safely reuse a palette-neutral identity.
    return actual


def renderer_fingerprint(root, patterns):
    rows = {CLIENT: client_fingerprint(root)}
    for pattern in [*patterns, 'patches/*.as', 'patches/*.inc', 'tools/*codegen.py',
                    'tools/game_config.py', 'tools/visual_assets.py', 'tools/media_fingerprints.py',
                    'resources/game_config.json', 'resources/local_ui.json',
                    'resources/cosmetic_catalog.json', 'assets/sprites/**/*', 'vendor/ruffle/*']:
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                rows[path.relative_to(root).as_posix()] = file_hash(path)
    return digest(rows)
