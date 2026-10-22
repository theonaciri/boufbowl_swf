"""Canonical AS3 patch selection for desktop and Android builds."""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ClientPatch:
    class_name: str
    source: Path


def discover(directory):
    patches = {}
    for source in sorted(directory.glob('*.as')):
        text = source.read_text()
        package = re.search(r'^package\s+([\w.]+)', text, re.M)
        declaration = re.search(r'\b(?:public|internal)\s+(?:(?:final|dynamic)\s+)*class\s+(\w+)', text)
        if not package or not declaration or declaration[1] != source.stem:
            raise ValueError(f'Invalid AS3 patch declaration: {source}')
        patches[source.name] = ClientPatch(package[1]+'.'+declaration[1], source)
    return patches


def client_patches(root=ROOT, platform='desktop'):
    if platform not in ('desktop', 'android'):
        raise ValueError(f'Unknown client platform: {platform}')
    patches = discover(root/'patches')
    if platform == 'android':
        for name, override in discover(root/'android/patches').items():
            if name in patches and patches[name].class_name != override.class_name:
                raise ValueError(f'Android override changes the package of {name}')
            patches[name] = override
    # Retain Android's previous source-path ordering for replacement dependencies.
    return tuple(sorted(patches.values(), key=lambda patch: patch.source))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', choices=('desktop', 'android'), default='desktop')
    parser.add_argument('--list', action='store_true', help='Include class/source entries')
    args = parser.parse_args()
    patches = client_patches(platform=args.platform)
    result = {'platform': args.platform, 'count': len(patches),
              'overrides': [p.source.name for p in patches if p.source.parent == ROOT/'android/patches']}
    if args.list:
        result['patches'] = [{'class': p.class_name, 'source': str(p.source.relative_to(ROOT))} for p in patches]
    print(json.dumps(result))


if __name__ == '__main__':
    main()
