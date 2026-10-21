"""Compatibility entry point for the Bun legal-page/static-site compiler."""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def outputs():
    result = subprocess.run([os.environ.get('BUN', 'bun'), str(ROOT/'tools/website/legal.mjs')],
                            cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    command = [os.environ.get('BUN', 'bun'), str(ROOT/'tools/website/build.mjs')]
    if args.check:
        command.append('--check')
    subprocess.run(command, cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
