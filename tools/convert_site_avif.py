"""Incrementally encode website stadium previews and the site logo as AVIF."""
import json
from pathlib import Path
import subprocess
import tempfile
from tools.media_fingerprints import digest, file_hash, read_json

ROOT = Path(__file__).resolve().parent.parent
QUALITY = 80


def encode_png(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        'avifenc', '--qcolor', str(QUALITY), '--qalpha', str(QUALITY),
        '--speed', '6', str(source), str(target),
    ], check=True)


def main():
    cache_path = ROOT/'.local/website/image-cache.json'
    cache = read_json(cache_path, {})
    manifest = json.loads((ROOT/'resources/stadium_art.json').read_text())
    pairs = [(ROOT/t['path'], ROOT/t['web_path']) for t in manifest['textures'].values()]
    pairs.append((ROOT/'assets/site/logo.webp', ROOT/'assets/site/logo.avif'))
    for source, target in pairs:
        key = target.relative_to(ROOT).as_posix()
        fingerprint = digest({'source': file_hash(source), 'recipe': file_hash(__file__)})
        previous = cache.get(key, {})
        if (previous.get('input') == fingerprint and target.is_file()
                and previous.get('output') == file_hash(target)):
            print('Reusing', key, flush=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.avif-', dir=target.parent) as temporary:
            png = source
            if source.suffix != '.png':
                png = Path(temporary)/'source.png'
                subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(source),
                                '-frames:v', '1', str(png)], check=True)
            encoded = Path(temporary)/'encoded.avif'
            encode_png(png, encoded)
            encoded.replace(target)
        cache[key] = {'input': fingerprint, 'output': file_hash(target)}
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_cache = cache_path.with_suffix('.building.json')
        temporary_cache.write_text(json.dumps(cache, indent=2)+'\n')
        temporary_cache.replace(cache_path)
        print(f'{source.relative_to(ROOT)} -> {key} ({QUALITY}% quality)', flush=True)


if __name__ == '__main__':
    main()
