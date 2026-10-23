"""Check the saved diagnostic observations, without treating event Hz as presentation FPS."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent
for name in ('bare','game-ui'):
    data=json.loads((root/f'results-{name}.json').read_text())
    assert len(data['samples'])==24,(name,'matrix incomplete')
    assert data['policy']=={'authoredHz':25,'browserSceneAt144':30,'nativeSceneAt144':50,'web144Accepted':False}
    canonical=data['synthetic']['rates'][0]['frames']
    for row in data['synthetic']['rates']:
        assert row['frames']==canonical and row['completion']==1
        assert row['finalX']==100 and row['interpolationError']<1e-8
        assert row['distinctPositions']==min(row['requested'],1000)+1
    for row in data['samples']:
        assert row['stage']==row['requested']
        assert row['elapsedMs']>0 and row['frames']==len(row['intervals'])
    print(name,': 24 samples; actual FrameController pose sequence, completion and SegmentTrajectory endpoint invariant')
for rate in (25,60,144,240):
    path=root/f'results-replay-{rate}.json'
    data=json.loads(path.read_text());row=data['samples'][0]
    assert row['sceneUpdates']>0 and row['sceneUpdates']==row['uiUpdates']
    assert row['positionWrites']>0 and row['stage']==row['requested']
    events=data['replayEvents']
    expected=['Playback mode 3D','Outgoing ResolutionDoneMessage','Incoming MATCH_END']
    indices=[next(i for i,event in enumerate(events) if marker in event) for marker in expected]
    assert indices==sorted(indices) and sum('Outgoing ResolutionDoneMessage' in event for event in events)==1
    print(path.name,': scene/UI updates equal; 3D → one ResolutionDone → MATCH_END')
forced=json.loads((root/'results-forced.json').read_text())
assert forced['samples'][0]['requested']==144 and forced['samples'][0]['stage']==30
print('Frontend forced rate: 144 requested, 30 retained; native execution must be reported separately.')
