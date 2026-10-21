"""Refresh published static files after a successful player bundle build."""
from pathlib import Path
import subprocess


def refresh_website(root, bun='bun'):
    root = Path(root).resolve()
    subprocess.run([bun, str(root/'tools/website/build.mjs'), '--root', str(root)],
                   cwd=root, check=True)
