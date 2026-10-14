"""Server-owned match classification and ranked statistics policy."""
POLICY_VERSION = 1


def result_kind(match):
    profiles = match.get('profiles', [])
    if len(profiles) != 2 or not all(profiles):
        return 'practice'
    if (match.get('result_policy_version') == POLICY_VERSION and
            match.get('mode') == 'ranked' and match.get('source') in ('matchmaking', 'tournament') and
            profiles[0] != profiles[1]):
        return 'ranked'
    # Matches without trustworthy queue provenance are casual.
    return 'casual'


def fresh_statistics():
    stats = {'wins':0, 'draws':0, 'defeats':0, 'rating':1000,
             'practice':{'wins':0,'draws':0,'defeats':0},
             'casual':{'wins':0,'draws':0,'defeats':0},
             'result_policy_version':POLICY_VERSION}
    return stats


def credit(stats, kind, outcome):
    counters = stats if kind == 'ranked' else stats[kind]
    counters[outcome] += 1
    if kind == 'ranked':
        stats['rating'] = max(0, stats['rating'] + (20 if outcome == 'wins' else -20 if outcome == 'defeats' else 0))
