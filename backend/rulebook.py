"""Versioned rulebook provenance, frozen with each new match."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

REGISTRY = Path(__file__).resolve().parent.parent / 'resources/rulebook.json'


def rulebook_snapshot(rules):
    policy = rules.get('simulation', {}).get('rulebook')
    if policy is None:
        return None
    registry = json.loads(REGISTRY.read_text())
    if policy['id'] != registry['id']:
        raise ValueError('Unknown rulebook identity')
    identifiers = [rule['id'] for rule in registry['rules']]
    if set(identifiers) != {f'C{i:02}' for i in range(1, 23)} or len(identifiers) != 22:
        raise ValueError('Rulebook must cover C01 through C22 exactly once')
    if any(not rule['sources'] or rule['status'] not in ('implemented','provisional','custom','pending') for rule in registry['rules']):
        raise ValueError('Every rule needs evidence and an explicit status')
    if any(source not in registry['sources'] for rule in registry['rules'] for source in rule['sources']):
        raise ValueError('A rule cites an unknown evidence source')
    snapshot = deepcopy(registry)
    snapshot['policy'] = deepcopy(policy)
    snapshot['match_policy'] = deepcopy(rules['match'])
    snapshot['class_attributes'] = deepcopy(rules['classes'])
    snapshot['class_abilities'] = deepcopy(rules['abilities'])
    snapshot.pop('policy_defaults')
    snapshot['sha256'] = hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return snapshot
