"""Replay a real goal in each stadium and verify its original celebration."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from tools.build_interaction_fixtures import fixture
from tools.flash_protocol import Codec
from tools.game_config import ROOT, STADIUMS
from tools.stadium_celebrations import celebrations


def goal_fixture(stadium):
    record = json.loads((ROOT / 'tests/fixtures/interactions/goal-record.json').read_text())
    record['presentation'] = {'interactions': True}
    replay = fixture('goal', record)
    info = replay['steps'][0]
    info['decoded']['matchStadium'] = STADIUMS.index(stadium) + 1
    info['hex'] = Codec().envelope(info['type'], info['decoded']).hex()
    replay['steps'][-1]['decoded'].update(leftScore=1, rightScore=0)
    replay['steps'][-1]['hex'] = Codec().envelope('MATCH_END', replay['steps'][-1]['decoded']).hex()
    return replay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stadiums', nargs='+', choices=STADIUMS, default=['BEACH'] + [s for s in STADIUMS if s != 'BEACH'])
    args = parser.parse_args()
    mapping = celebrations(ROOT)
    evidence = ROOT / 'evidence/stadium-celebrations'
    evidence.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='boufbowl-goal-celebrations-') as tmp:
        for stadium in args.stadiums:
            target = Path(tmp) / (stadium + '.json')
            target.write_text(json.dumps(goal_fixture(stadium)))
            print('Testing ' + stadium + ': ' + mapping[stadium]['animation'], flush=True)
            subprocess.run([sys.executable, '-m', 'tools.smoke_mock', '--fixture', str(target),
                            '--require-cinematic', '--require-celebration', mapping[stadium]['animation'],
                            '--timeout', '120'], cwd=ROOT, check=True)
            for original, suffix in [('mock-engine-trace.log', '.log'), ('mock-stadium-celebration.png', '.png')]:
                shutil.copyfile(ROOT / 'evidence' / original, evidence / (stadium.lower() + suffix))
            print('Verified ' + stadium, flush=True)


if __name__ == '__main__':
    main()
