"""Assemble public website files and validate a deployable overlay without private state."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from backend.server import DOWNLOAD_FILES, download_path, site_manifest
from tools.build_legal_pages import outputs

PAGES = ('index.html', 'play.html', 'browser.html')
FRONTEND = ('home.js', 'home.css', 'restoration.js', 'restoration.css', 'legal.css')


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_suffix('.building.json')
    staging.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    staging.replace(path)


def public_files(root):
    root = Path(root).resolve()
    paths = [*PAGES, *FRONTEND, *outputs()]
    paths += ['bin/boufbowl-client-1.9.6.swf']
    for folder in ('assets', 'vendor', 'resources'):
        paths += [p.relative_to(root).as_posix() for p in (root/folder).rglob('*') if p.is_file()]
    for relative in sorted(set(paths)):
        path = root/relative
        if not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError('Missing or unsafe public file: '+relative)
        if path.name.endswith(('.building.webp', '.building.json')):
            continue
        yield relative, path


def delivery(root, destination, check=False):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    if destination == root or destination in root.parents or any(destination.is_relative_to(root/p) for p in ('assets','resources','vendor','bin')):
        raise ValueError('Delivery directory must be separate from source assets')
    from tools.build_restoration_data import homepage_assets
    missing=[a['path'] for a in homepage_assets(root) if not a['available']]
    if missing:
        raise ValueError('Missing homepage assets: '+', '.join(missing))
    if destination.is_relative_to(root) and destination.relative_to(root).parts[0] != '.local':
        raise ValueError('Inside the checkout, use a delivery directory under .local')
    if destination.exists() and any(destination.iterdir()) and not (destination/'delivery.json').is_file():
        raise ValueError('Refusing to replace a directory without a website delivery manifest')
    files = dict(public_files(root))
    for route, (relative, _) in DOWNLOAD_FILES.items():
        path = download_path(root, relative)
        if path:
            files[route.lstrip('/')] = path
    expected = {name: {'bytes':path.stat().st_size, 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                for name,path in files.items()}
    report = {'version':1, 'files':expected, 'file_count':len(files),
              'bytes':sum(f['bytes'] for f in expected.values()),
              'downloads':site_manifest(root)['downloads']}
    if check:
        saved = destination/'delivery.json'
        if not saved.is_file() or json.loads(saved.read_text()) != report:
            raise ValueError('Website delivery is stale; run python3 -m tools.build_website')
        actual={p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()}
        if actual != set(expected)|{'delivery.json'}:
            raise ValueError('Website delivery contains missing or unexpected files')
        for name, entry in expected.items():
            path = destination/name
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
                raise ValueError('Missing or altered delivery file: '+name)
        return report
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Stage the complete overlay before replacing the previous successful delivery.
    with tempfile.TemporaryDirectory(prefix='website-', dir=destination.parent) as folder:
        stage = Path(folder)/'public'
        stage.mkdir()
        for name,path in files.items():
            target = stage/name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
        write_json(stage/'delivery.json', report)
        backup=destination.with_name(destination.name+'.previous')
        if backup.exists():
            raise ValueError('Previous delivery backup already exists: '+str(backup))
        if destination.exists():
            destination.rename(backup)
        try:
            stage.rename(destination)
        except Exception:
            if backup.exists():backup.rename(destination)
            raise
        if backup.exists():shutil.rmtree(backup)
    return report
