"""Keep website-only stadium previews out of packaged game assets."""
from pathlib import Path


def website_stadium_preview(filename):
    path = Path(filename)
    return (path.suffix.lower() == '.avif'
            and path.parent.parts[-3:] == ('assets', 'textures', 'stadiums'))


def ignore_website_stadium_previews(directory, names):
    """shutil.copytree ignore callback; preserve the PNG game textures."""
    return [name for name in names if website_stadium_preview(Path(directory) / name)]
