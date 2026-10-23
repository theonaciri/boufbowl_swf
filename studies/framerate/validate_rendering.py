"""Validate saved renderer correctness evidence; do not assert hardware FPS gains."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent/'rendering'
provenance=json.loads((root/'provenance.json').read_text())
assert provenance['movedActors']==[11,12,13,14,15,21,22,23,24,25]
assert provenance['moveEvents']==260
for mode in ('baseline','retained'):
    result=json.loads((root/mode/'results-bare.json').read_text())
    assert len(result['benchmarks'])==3
    for sample in result['benchmarks']:
        assert sample['iterations']==300 and sample['actors']==10 and sample['leavesPerActor']==30
        expected=(90000,89700) if mode=='baseline' else (300,0)
        assert (sample['stageAdditions'],sample['stageRemovals'])==expected
    if mode=='retained':assert result['sessionCheck']['ok'] is True
    print(mode,': three real session benchmarks; stage lifecycle counts verified')
for mode,rate in [('baseline',60),('retained',60),('retained',240),('retained-reception',240)]:
    result=json.loads((root/mode/f'results-replay-{rate}.json').read_text())
    events=result['replayEvents']; sample=result['samples'][0]
    playback=next(i for i,e in enumerate(events) if 'Playback mode 3D' in e)
    done=[i for i,e in enumerate(events) if 'Outgoing ResolutionDoneMessage' in e]
    ended=next(i for i,e in enumerate(events) if 'Incoming MATCH_END' in e)
    assert len(done)==1 and playback<done[0]<ended
    assert sample['sceneUpdates']==sample['uiUpdates']>0
    assert sample['sceneRates']=={str(rate):sample['sceneUpdates']}
    assert result['renderProfile']['scene']['count']>=sample['sceneUpdates']
    assert result['renderProfile']['render']['count']>0
    print(mode,rate,': ordered 3D completion, matching scene/UI updates, chosen rate retained')
print('Wine/physical 240 Hz presentation is not validated by these browser probes.')
