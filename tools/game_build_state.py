"""Cheap shared cache decision for the game and player build entry points."""
from tools.media_fingerprints import CLIENT, file_hash, logic_fingerprint, read_json


def game_build_reason(root):
    client = root / CLIENT
    if not client.is_file():
        return 'compiled client missing'
    receipt = read_json(root / '.local/game-build.json', {})
    if not isinstance(receipt, dict) or not receipt.get('logic'):
        return 'completed build record missing or invalid'
    if receipt.get('client') != file_hash(client):
        return 'compiled client changed outside the build'
    if receipt['logic'] != logic_fingerprint(root):
        return 'shared sources or configuration changed'
    # Keep palettes separate from the palette-neutral logic identity used by
    # per-character media caches, while tracking their compiled UI defaults.
    if receipt.get('palette') != file_hash(root / 'resources/palettes.json'):
        return 'palette changed or its build record needs upgrading'
    return None


def game_rebuild_required(root):
    return game_build_reason(root) is not None
