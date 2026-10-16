"""Compare isolated portrait render workers on the same balanced native-pose sample."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from tools.site_portraits import ROOT, renderer_inputs, webp_size
from tools.site_delivery import write_json

CHARACTERS=('cra-1','cra-2','hero-513','hero-514','hero-516','hero-518')
POSES=('default','alternate','action-05','action-10')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffdec',required=True,type=Path)
    parser.add_argument('--java',default=os.environ.get('JAVA','java'))
    parser.add_argument('--bun',default=os.environ.get('BUN','bun'))
    parser.add_argument('--jobs',type=int,nargs='+',choices=range(1,5),default=[1,2,3])
    args=parser.parse_args()
    report={'date':datetime.now(timezone.utc).isoformat(),'logical_cpus':os.cpu_count(),
            'characters':CHARACTERS,'poses':POSES,'renderer_inputs':renderer_inputs(),'results':[]}
    for jobs in args.jobs:
        if renderer_inputs()!=report['renderer_inputs']:
            raise RuntimeError('Renderer changed between benchmark configurations; restart the comparison')
        print(f'Benchmarking {jobs} worker(s), {len(CHARACTERS)*len(POSES)} portraits...',flush=True)
        command=[sys.executable,'-m','tools.build_website','--force','--jobs',str(jobs),
                 '--ffdec',str(args.ffdec),'--java',args.java,'--bun',args.bun]
        for character in CHARACTERS:command+=['--character',character]
        for pose in POSES:command+=['--pose',pose]
        subprocess.run(command,cwd=ROOT,check=True)
        build=json.loads((ROOT/'.local/website/build-report.json').read_text())
        result=build['timings']['workers']
        if result['portraits']!=len(CHARACTERS)*len(POSES):raise RuntimeError('Incomplete benchmark')
        if sum(w['character_initializations'] for w in result['workers'])!=len(CHARACTERS):
            raise RuntimeError('Character state was not reused within a batch')
        for character in CHARACTERS:
            for pose in POSES:
                if webp_size(ROOT/f'assets/site/restoration/{character}-{pose}.webp')[1]!=1080:
                    raise RuntimeError('Incorrect portrait resolution')
        report['results'].append({**result,'total_seconds':build['timings']['total_seconds']})
        write_json(ROOT/'.local/website/benchmark-report.json',report)
    winner=min(report['results'],key=lambda r:r['seconds'])
    print(f"Fastest measured configuration: --jobs {winner['jobs']} ({winner['seconds']:.2f}s rendering)")
    print('Report: .local/website/benchmark-report.json')


if __name__=='__main__':
    main()
