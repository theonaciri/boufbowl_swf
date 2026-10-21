"""Call the Bun static-site compiler from the media generation pipeline."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
PAGES = ('index.html', 'play.html', 'browser.html', 'admin.html', 'website-activity.html', 'moderation.html', 'tournaments.html', 'assets-admin.html')
FRONTEND = ('home.js', 'home.css', 'contributions.css', 'restoration.css', 'restoration.js', 'site-activity.js', 'contributions.js',
            'website-activity.js', 'legal.css', 'admin.js', 'admin.css', 'moderation.js', 'tournaments.js', 'assets-admin.js')


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_suffix('.building.json')
    staging.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    staging.replace(path)


def delivery(root, destination, check=False, bun='bun'):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    from tools.build_restoration_data import homepage_assets
    missing = [a['path'] for a in homepage_assets(root) if not a['available']]
    if missing:
        raise ValueError('Missing homepage assets: '+', '.join(missing))
    command = [bun, str(ROOT/'tools/website/build.mjs'), '--root', str(root), '--output', str(destination)]
    if check:
        command.append('--check')
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip() or result.stdout.strip())
    print(result.stdout, end='')
    return json.loads((destination/'delivery.json').read_text())
