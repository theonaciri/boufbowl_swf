"""Check saved runtime evidence for the maintained policy, without its FPS bypass."""
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent / 'applied'
control = json.loads((root / 'results-bare.json').read_text())
assert control['environment']['productionPolicy'] is True
assert control['checks']['sharedSmoke']['ok'] is True
assert control['checks']['nativeBranchSharedSmoke']['ok'] is True
assert control['checks']['nativeBranchSharedSmoke']['runtime'] == 'native-path'
assert control['checks']['launchBrowser'] == 144
assert control['policy']['nativeSceneAt144'] == 144
assert control['policy']['web144Accepted'] is True
for row in control['checks']['valid']:
    assert row['accepted'] is True
    assert row['settings']['stage'] == row['requested']
    assert row['settings']['scene25'] == row['requested']
    assert row['settings']['scene50'] == row['requested']
assert [row['requested'] for row in control['checks']['valid']] == [25,30,50,60,90,120,144,240]
assert all(row['accepted'] is False and row['stage'] == 144
           for row in control['checks']['invalid'])
assert len(control['checks']['invalid']) == 7
for row in control['synthetic']['rates']:
    assert row['frames'] == list(range(26))
    assert row['completion'] == 1 and row['finalX'] == 100
    assert row['interpolationError'] < 1e-12
print('AS3 settings: eight rates, invalid input, shared smoke and authored timing passed')

for rate, runtime in [(25, 'ruffle'), (60, 'flash'), (144, 'ruffle'), (240, 'ruffle')]:
    result = json.loads((root / f'results-replay-{rate}.json').read_text())
    assert result['environment']['productionPolicy'] is True
    assert result['environment']['runtimePath'] == runtime
    events = result['replayEvents']
    playback = next(i for i, event in enumerate(events) if 'Playback mode 3D' in event)
    done = [i for i, event in enumerate(events) if 'Outgoing ResolutionDoneMessage' in event]
    ended = next(i for i, event in enumerate(events) if 'Incoming MATCH_END' in event)
    assert len(done) == 1 and playback < done[0] < ended
    sample = result['samples'][0]
    assert sample['requested'] == result['environment']['target'] == rate
    assert sample['sceneUpdates'] == sample['uiUpdates'] > 0
    assert sample['positionWrites'] > 0
    assert sample['sceneRates'] == {str(rate): sample['sceneUpdates']}
    assert sample['stage'] == rate
    print(f'{rate} ({runtime} branch in Ruffle): scene rate retained, ordered completion, one UI update per scene')

print('Native runtime and physical high-refresh presentation remain unverified.')

overlay = json.loads((root / 'results-game-ui.json').read_text())
assert overlay['sharedSmoke']['ok'] is True
assert [row['requested'] for row in overlay['overlayChecks']] == [30,120,25]
for row in overlay['overlayChecks']:
    assert row['stage'] == row['scene'] == row['requested']
    assert re.fullmatch(r'FPS: \d+ / ' + str(row['requested']), row['text'])
print('Overlay reports measured and requested rates after live changes.')
