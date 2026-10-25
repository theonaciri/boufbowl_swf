"""The original starter club, with a fresh lineup and appearance each match."""
import json
from pathlib import Path
import secrets


ROOT = Path(__file__).resolve().parent.parent
PALETTES = json.loads((ROOT / 'resources/palettes.json').read_text())
CLASS_PALETTES = {entry['class_id']: entry for entry in PALETTES['class_palettes']}
TEAM_COLORS = tuple(dict.fromkeys(
    value for palette in PALETTES['club_palettes']
    for value in palette['colors']))
SIGILS = json.loads((ROOT / 'protocol/client_contract.json').read_text())['enums']


def color_distance(a, b):
    return sum(abs(a[key] - b[key]) for key in ('r', 'g', 'b'))


def random_appearance(rng, opponent_color):
    colors = [dict(zip(('r', 'g', 'b'), bytes.fromhex(value))) for value in TEAM_COLORS]
    # Choose the primary before the accents so clash avoidance cannot collapse
    # the kit and blazon into a single color.
    primary = rng.choice([c for c in colors if opponent_color is None or
                          color_distance(c, opponent_color) >= 180])
    secondary = rng.choice([c for c in colors if color_distance(c, primary) >= 240])
    pattern = rng.choice([c for c in colors if color_distance(c, primary) >= 180 and
                          color_distance(c, secondary) >= 180])
    return dict(firstColor=primary, secondColor=secondary, patternColor=pattern,
                sigilBackground=rng.choice(tuple(SIGILS['SigilBackground'].values())),
                sigilCharge=rng.choice(tuple(SIGILS['SigilCharge'].values())))


def default_cpu_club(opponent_color=None):
    combinations = [(1, 1), (1, 2), (4, 2), (3, 2), (6, 1),
                    (2, 1), (5, 2), (7, 1), (8, 2), (10, 1)]
    names = ['Aria', 'Baff', 'Cora', 'Dara', 'Elia', 'Fara', 'Gust', 'Hana', 'Iris', 'Jora']
    def character_colors(cls, gender):
        palette = CLASS_PALETTES[cls]
        defaults = palette.get('defaults', {}).get('female' if gender == 2 else 'male', {})
        return {field: dict(zip(('r', 'g', 'b'), bytes.fromhex(defaults.get(kind,
                    palette[kind][min(gender - 1, len(palette[kind]) - 1)]))))
                for field, kind in [('hairColor', 'hair'), ('skinColor', 'skin'), ('eyeColor', 'eyes')]}
    players = [dict(id=str(i + 1), name=name, boufbowlerClass=cls, gender=gender,
                    paletteId=CLASS_PALETTES[cls]['id'], **character_colors(cls, gender))
               for i, (name, (cls, gender)) in enumerate(zip(names, combinations))]
    starters = players[:5]
    rng = secrets.SystemRandom()
    rng.shuffle(starters)
    return dict(clubId='cpu', clubName='CPU team', boufbowler=starters + players[5:],
                **random_appearance(rng, opponent_color))
