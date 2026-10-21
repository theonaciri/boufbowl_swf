"""Export original tactical-grid cubes, using their native character frame labels."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import zlib
from tools.heraldry import tags

SYMBOL = 'com.ankamagames.boufbowl.match.strategic.boufbowler.BoufbowlerCubeSprite'


def frames(source):
    raw = Path(source).read_bytes()
    body = zlib.decompress(raw[8:]) if raw[:3] == b'CWS' else raw[8:]
    sprites, symbols = {}, {}
    for code, value in tags(body, (5 + 4*(body[0] >> 3) + 7)//8 + 4):
        if code == 39:
            sprites[struct.unpack_from('<H', value)[0]] = value
        elif code == 76:
            offset = 2
            for _ in range(struct.unpack_from('<H', value)[0]):
                identity = struct.unpack_from('<H', value, offset)[0]
                offset += 2
                end = value.index(0, offset)
                symbols[value[offset:end].decode()] = identity
                offset = end + 1
    identity = symbols[SYMBOL]
    result, frame = {}, 1
    for code, value in tags(sprites[identity], 4):
        if code == 43:
            label = value.split(b'\0')[0].decode()
            result[int(label.removeprefix('id_'))] = frame
        elif code == 1:
            frame += 1
    return identity, result


def build(root, characters, ffdec=None, java='java', force=False, check=False):
    root = Path(root)
    source = root/'bin/boufbowl-client-1.9.6.swf'
    identity, mapping = frames(source)
    expected = {c['hero'] or c['class_id']*10+c['gender'] for c in characters}
    if expected != set(mapping)-{0}:
        raise ValueError('Character roster and native grid icons do not match')
    directory = root/'assets/site/restoration/grid-icons'
    manifest_path = directory/'manifest.json'
    from tools.media_fingerprints import client_fingerprint
    fingerprint = hashlib.sha256(client_fingerprint(root).encode()+Path(__file__).read_bytes()).hexdigest()
    previous = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    valid = previous.get('fingerprint') == fingerprint and set(previous.get('files', {})) == {str(i) for i in expected}
    for key, digest in previous.get('files', {}).items():
        path = directory/f'{key}.png'
        valid = valid and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest
    if check:
        if not valid:
            raise ValueError('Grid icons are stale; run the website build with --ffdec and --java')
        return
    if valid and not force:
        print(f'Reusing {len(expected)} original grid icons', flush=True)
        return
    if not ffdec or not Path(ffdec).is_file():
        raise ValueError('Grid icon export needs --ffdec /path/to/ffdec.jar (and --java if Java is not on PATH)')
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='boufbowl-grid-icons-') as temporary:
        completed = subprocess.run([java, '-jar', str(Path(ffdec).resolve()), '-selectid', str(identity),
            '-select', f'{identity}:1-{max(mapping.values())}', '-zoom', '4', '-ignorebackground',
            '-format', 'sprite:png', '-export', 'sprite', temporary, str(source)],
            capture_output=True, text=True, timeout=120)
        if completed.returncode:
            raise RuntimeError(completed.stdout+completed.stderr)
        files = {}
        for skin in sorted(expected):
            matches = list(Path(temporary).rglob(f'{mapping[skin]}.png'))
            if len(matches) != 1:
                raise ValueError(f'Missing or ambiguous icon export for {skin}')
            data = matches[0].read_bytes()
            if data[:8] != b'\x89PNG\r\n\x1a\n':
                raise ValueError('Invalid exported PNG')
            shutil.copyfile(matches[0], directory/f'{skin}.png')
            files[str(skin)] = hashlib.sha256(data).hexdigest()
    manifest_path.write_text(json.dumps({'fingerprint':fingerprint, 'files':files}, indent=2)+'\n')
    print(f'Exported {len(files)} original grid icons at 4× resolution', flush=True)
