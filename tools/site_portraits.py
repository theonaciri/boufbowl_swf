"""Describe native portrait exports and verify their palette provenance and size."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import re
import zlib

ROOT = Path(__file__).resolve().parent.parent
TEAM_COLOR_OVERRIDES = {508: '000000'}  # Evangelyne's black team kit, website exports only.
POSES = {
    'default': ('Vestiaire', 'BoufbowlerIllustrationDefaultPosing'),
    'winner': ('Victoire', 'BoufbowlerIllustrationWinnerPosing'),
    'versus': ('Face-à-face', 'BoufbowlerIllustrationVersusPosing'),
    'loser': ('Défaite', 'BoufbowlerIllustrationLooserPosing'),
    'winner-default': ('Victoire par forfait', 'BoufbowlerIllustrationWinnerByDefaultPosing'),
    'loser-default': ('Défaite par forfait', 'BoufbowlerIllustrationLooserByDefaultPosing'),
    'draw': ('Match nul', 'BoufbowlerIllustrationDrawPosing'),
    'alternate': ('Accroupi', 'boufbowler1_posing_11'),
    'action-01': ('Lancer', 'boufbowler1_posing01'),
    'action-04': ('Plongeon', 'boufbowler1_posing04'),
    'action-05': ('Ballon · gros plan', 'boufbowler1_posing05'),
    'action-06': ('Acrobatie', 'boufbowler1_posing06'),
    'action-07': ('Rotation', 'boufbowler1_posing07'),
    'action-09': ('Déséquilibre', 'boufbowler1_posing09'),
    'action-10': ('Envol', 'boufbowler1_posing10'),
    'action-13': ('Reprise acrobatique', 'boufbowler1_posing13'),
    'action-02': ('Esquive', 'boufbowler2_posing02'),
    'action-03': ('Tacle glissé', 'boufbowler2_posing03'),
}
GROUPS = dict(zip(('default', 'winner', 'versus', 'loser', 'winner-default', 'loser-default', 'draw', 'alternate'),
                  ('boufbowler1_posing_10', 'boufbowler1_posing_21', 'boufbowler1_posing_25', 'boufbowler1_posing_24',
                   'boufbowler1_posing_22', 'boufbowler1_posing_26', 'boufbowler1_posing_23', 'boufbowler1_posing_11')))


def native_groups(path):
    """Read exported pose symbols and class/gender frame labels from the SWF tags."""
    data = Path(path).read_bytes()
    data = zlib.decompress(data[8:]) if data[:3] == b'CWS' else data[8:]
    start = (5 + 4*(data[0] >> 3) + 7)//8 + 4
    def tags(content, offset):
        while offset + 2 <= len(content):
            header = struct.unpack_from('<H', content, offset)[0]
            offset += 2
            size = header & 63
            if size == 63:
                size = struct.unpack_from('<I', content, offset)[0]
                offset += 4
            yield header >> 6, content[offset:offset+size]
            offset += size
    symbols, frames = {}, {}
    for kind, content in tags(data, start):
        if kind == 76:
            count = struct.unpack_from('<H', content)[0]
            offset = 2
            for _ in range(count):
                identity = struct.unpack_from('<H', content, offset)[0]
                offset += 2
                end = content.index(b'\0', offset)
                symbols[content[offset:end].decode()] = identity
                offset = end + 1
        elif kind == 39:
            identity = struct.unpack_from('<H', content)[0]
            frames[identity] = {value.split(b'\0')[0].decode() for tag, value in tags(content, 4) if tag == 43}
    return {name: frames[identity] for name, identity in symbols.items()
            if re.fullmatch(r'boufbowler[12]_posing_?\d+', name)}


def audit_native_poses(characters, root=ROOT):
    root = Path(root)
    sources = {
        False: native_groups(root/'assets/artworks/cutscene-boufbowler-repository.swf'),
        True: native_groups(root/'assets/artworks/cutscene-illustration.swf'),
    }
    for action, groups in sources.items():
        expected = {GROUPS.get(key, value[1]) for key, value in POSES.items() if key.startswith('action-') == action}
        if set(groups) != expected:
            raise ValueError('Native pose symbols changed; audit the source libraries again')
    for key, value in POSES.items():
        group = GROUPS.get(key, value[1])
        labels = sources[key.startswith('action-')][group]
        for c in characters:
            identity = c['hero'] or c['class_id']*10+c['gender']
            if 'cg_'+str(identity) not in labels:
                raise ValueError(f"Missing original frame for {c['id']}: {group}")


def export_plan(characters, settings):
    tasks = []
    for c in characters:
        entries = ([p for p in settings['hero_palettes'] if p['unique_character'] == c['hero']]
                   if c['hero'] else [p for p in settings['class_palettes'] if p['class_id'] == c['class_id']])
        if not entries:
            raise ValueError('Missing default palette: ' + c['id'])
        entries = entries[:1]  # Same first/default palette as the native editor.
        for p in entries:
            style = 'unique' if c['hero'] else p['style'].lower()
            gender = 'male' if c['gender'] == 1 else 'female'
            defaults = p.get('defaults', {}).get(gender, {})
            colors = {k: defaults.get(k, p[k][0 if c['hero'] or c['gender'] == 1 else min(1, len(p[k])-1)])
                      for k in ('hair', 'skin', 'eyes')}
            for pose, (_, symbol) in POSES.items():
                tasks.append({'id': c['id'] + '-' + pose,
                              'character': c['id'], 'cls': c['class_id'], 'gender': c['gender'],
                              'hero': c['hero'], 'style': style, 'palette': p['id'], 'native_group': GROUPS.get(pose,symbol),
                              'colors': colors, **({'team_color': TEAM_COLOR_OVERRIDES[c['hero']]} if c['hero'] in TEAM_COLOR_OVERRIDES else {}), 'pose': pose, 'symbol': 'action:'+symbol if pose.startswith('action-') else 'alternate' if pose == 'alternate' else symbol})
    return tasks



def capture_source(root=ROOT):
    source = (Path(root)/'tools/site_portrait_capture.as.inc').read_text()
    color = '0x3578cf'
    for hero, override in TEAM_COLOR_OVERRIDES.items():
        color = f'hero=={hero} ? 0x{override} : ({color})'
    original = 'Color3.fromRgbUInt(0x3578cf)'
    if source.count(original) != 2:
        raise ValueError('Team color injection points changed; review the export override')
    # Other characters retain exactly the same renderer and color. Only override
    # tasks gain a team_color field, invalidating their existing cached exports.
    return source.replace(original, f'Color3.fromRgbUInt({color})')


def renderer_inputs(root=ROOT):
    root=Path(root)
    files=['tools/site_portrait_capture.as.inc','tools/site_portrait_capture.js',
           'patches/StartUpApplicationCommand.as','tools/game_config.py','tools/visual_assets.py',
           'bin/boufbowl-client-1.9.6.swf','resources/game_config.json','vendor/ruffle/ruffle.js','assets/artworks/cutscene-boufbowler-repository.swf',
           'assets/artworks/cutscene-illustration.swf']
    files += [p.relative_to(root).as_posix() for p in sorted((root/'vendor/ruffle').glob('*.wasm'))]
    return {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in files}


def render_fingerprint(task, inputs):
    relevant={k:v for k,v in inputs.items() if task['pose'].startswith('action-') or not k.endswith('cutscene-illustration.swf')}
    return hashlib.sha256(json.dumps({'task':task,'inputs':relevant,'height':1080,'quality':92},sort_keys=True).encode()).hexdigest()


def reusable(task, entry, path, inputs):
    try:
        return (entry.get('render_fingerprint')==render_fingerprint(task,inputs)
                and all(entry.get(k)==v for k,v in task.items()) and webp_size(path)[1]==1080
                and entry.get('sha256')==hashlib.sha256(Path(path).read_bytes()).hexdigest())
    except (OSError, ValueError, struct.error):
        return False


def webp_size(path):
    data = Path(path).read_bytes()
    if data[:4] != b'RIFF' or data[8:12] != b'WEBP':
        raise ValueError('Invalid WebP: ' + str(path))
    offset = 12
    while offset + 8 <= len(data):
        kind, size = data[offset:offset+4], struct.unpack_from('<I', data, offset+4)[0]
        body = data[offset+8:offset+8+size]
        if kind == b'VP8X':
            return int.from_bytes(body[4:7], 'little')+1, int.from_bytes(body[7:10], 'little')+1
        if kind == b'VP8 ':
            width, height = struct.unpack_from('<HH', body, 6)
            return width & 0x3fff, height & 0x3fff
        if kind == b'VP8L':
            bits = int.from_bytes(body[1:5], 'little')
            return (bits & 0x3fff)+1, ((bits >> 14) & 0x3fff)+1
        offset += 8 + size + (size % 2)
    raise ValueError('Missing WebP dimensions: ' + str(path))


def manifest(root=ROOT):
    root = Path(root)
    characters = json.loads((root/'assets/site/restoration/inventory.json').read_text())['characters']
    audit_native_poses(characters, root)
    settings = json.loads((root/'resources/palettes.json').read_text())
    previous_path=root/'assets/site/restoration/portraits.json'
    previous={e['id']:e for e in json.loads(previous_path.read_text()).get('exports',[])} if previous_path.exists() else {}
    cache_path=root/'.local/website/portrait-cache.json'
    cache=json.loads(cache_path.read_text()) if cache_path.exists() else {}
    exports = []
    for task in export_plan(characters, settings):
        path = 'assets/site/restoration/' + task['id'] + '.webp'
        width, height = webp_size(root/path)
        if height != 1080:
            raise ValueError('Portrait not exported at double resolution: ' + path)
        digest=hashlib.sha256((root/path).read_bytes()).hexdigest()
        prior=cache.get(task['id'],{})
        if prior.get('sha256')!=digest:prior=previous.get(task['id'],{})
        exports.append({**task, 'path': path, 'width': width, 'height': height,
                        'render_fingerprint':prior.get('render_fingerprint') if prior.get('sha256')==digest else None,
                        'sha256':digest})
    data = {
        'version': 1, 'source': 'assets/artworks/cutscene-boufbowler-repository.swf',
        'source_sha256': hashlib.sha256((root/'assets/artworks/cutscene-boufbowler-repository.swf').read_bytes()).hexdigest(),
        'action_source': 'assets/artworks/cutscene-illustration.swf',
        'action_source_sha256': hashlib.sha256((root/'assets/artworks/cutscene-illustration.swf').read_bytes()).hexdigest(),
        'palettes_sha256': hashlib.sha256((root/'resources/palettes.json').read_bytes()).hexdigest(),
        'renderer_inputs':renderer_inputs(root),
        'render': {'character_height': 1000, 'canvas_height': 1080, 'previous_canvas_height': 540,
                   'transparent': True, 'team_color': '3578cf', 'team_color_overrides': {str(k):v for k,v in TEAM_COLOR_OVERRIDES.items()}, 'encoder': 'chromium-webp', 'quality': 0.92},
        'poses': [{'id': key, 'label': value[0], 'symbol': value[1], 'native_group': GROUPS.get(key,value[1])}
                  for key, value in POSES.items()],
        'exports': exports,
    }
    data['revision'] = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--audit', action='store_true')
    args = parser.parse_args()
    if args.audit:
        characters = json.loads((ROOT/'assets/site/restoration/inventory.json').read_text())['characters']
        audit_native_poses(characters)
        print(f'Confirmed {len(POSES)} native poses for all {len(characters)} character variants.')
    elif args.plan:
        characters = json.loads((ROOT/'assets/site/restoration/inventory.json').read_text())['characters']
        print(json.dumps(export_plan(characters, json.loads((ROOT/'resources/palettes.json').read_text())), ensure_ascii=False))
    else:
        path = ROOT/'assets/site/restoration/portraits.json'
        data = manifest()
        if args.check:
            if json.loads(path.read_text()) != data:
                raise SystemExit('Portrait manifest is stale; re-export with the current palettes')
            print(f"Verified {len(data['exports'])} native portraits at 1080 px.")
        else:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
            print(f"Indexed {len(data['exports'])} portraits.")
