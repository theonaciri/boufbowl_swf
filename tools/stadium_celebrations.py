"""Original goal celebrations, independent of replacement stadium geometry."""
import json
from pathlib import Path
import zlib


def celebrations(root):
    from tools.game_config import STADIUMS
    data = json.loads((Path(root) / 'resources/stadium_celebrations.json').read_text())
    if set(data) != set(STADIUMS):
        raise ValueError('Goal celebrations must cover every stadium')
    swf = (Path(root) / 'assets/artworks/cutscene-illustration.swf').read_bytes()
    symbols = zlib.decompress(swf[8:]) if swf[:3] == b'CWS' else swf[8:]
    for stadium, entry in data.items():
        if not entry['animation'] or entry['animation'].encode() + b'\0' not in symbols:
            raise ValueError('Missing goal celebration animation for ' + stadium)
        # Some original reaction sounds are absent; they must not block the movie.
    return data
