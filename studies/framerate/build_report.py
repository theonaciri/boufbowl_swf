"""Build a self-contained, explicitly scoped visualization from saved measurements."""
import json
from pathlib import Path
from statistics import median
root=Path(__file__).resolve().parent
rates=[25,30,50,60,90,120,144,240]
summary={'contexts':{},'replays':[],'native':'blocked: AIR developer license','synthetic':[]}
summary['applied']=[]
for path in sorted((root/'applied').glob('results-replay-*.json')):
    result=json.loads(path.read_text())
    sample=result['samples'][0]
    summary['applied'].append({**{key:sample[key] for key in ('requested','sceneUpdates','uiUpdates','sceneRates')},
                              'runtime':result['environment']['runtimePath']})
for name in ('bare','game-ui'):
    data=json.loads((root/f'results-{name}.json').read_text())
    rows=[]
    for rate in rates:
        samples=[s for s in data['samples'] if s['requested']==rate]
        rows.append({'requested':rate,'events':median(s['frameEventHz'] for s in samples),
                     'raf':median(s['rafHz'] for s in samples),
                     'minimum':min(s['frameEventHz'] for s in samples),'maximum':max(s['frameEventHz'] for s in samples),
                     'duplicatePercent':100*sum(s['duplicates'] for s in samples)/sum(s['frames'] for s in samples)})
    summary['contexts'][name]=rows
    if name=='bare':summary['synthetic']=data['synthetic']['rates']
for path in sorted(root.glob('results-replay-*.json')):
    row=json.loads(path.read_text())['samples'][0]
    summary['replays'].append({k:row[k] for k in ('requested','wallMs','frames','sceneUpdates','uiUpdates','positionWrites')})
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
template=(root/'report-template.html').read_text()
(root/'report.html').write_text(template.replace('__STUDY_DATA__',json.dumps(summary)))
print(json.dumps({'contexts':2,'timingSamples':48,'replays':len(summary['replays']),'report':str(root/'report.html')}))
