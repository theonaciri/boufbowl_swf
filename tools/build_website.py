"""Generate website portraits from native Flash vectors, then refresh restoration data."""
import argparse
from collections import deque
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
from tools.site_delivery import delivery, write_json
from tools.build_legal_pages import outputs as legal_outputs
from backend.server import site_manifest
from tools.site_portraits import ROOT, POSES, export_plan, manifest, webp_size, renderer_inputs, render_fingerprint, reusable
from tools.game_config import load_config, startup_source
from tools.build_restoration_data import audit
from tools.site_grid_icons import build as build_grid_icons


def main():
    started = time.perf_counter()
    timings = {}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'.local/website/dist', help='Public website delivery directory')
    parser.add_argument('--ffdec', type=Path, default=os.environ.get('FFDEC_JAR'))
    parser.add_argument('--java', default=os.environ.get('JAVA', 'java'))
    parser.add_argument('--bun', default=os.environ.get('BUN', 'bun'))
    parser.add_argument('--jobs', type=int, choices=range(1,5), default=1, help='Independent render pages (default: 1; software rendering benchmark winner)')
    parser.add_argument('--pose', action='append', choices=list(POSES), help='Render only this pose (repeatable)')
    parser.add_argument('--character', action='append', help='Render only this character ID (repeatable)')
    parser.add_argument('--force', action='store_true', help='Re-render every portrait')
    parser.add_argument('--check', action='store_true', help='Verify existing exports without rendering')
    args = parser.parse_args()
    directory = ROOT/'assets/site/restoration'
    settings = json.loads((ROOT/'resources/palettes.json').read_text())
    tasks = export_plan(audit()['characters'], settings)
    build_grid_icons(ROOT, audit()['characters'], args.ffdec, args.java, args.force, args.check)
    old_path = directory/'portraits.json'
    old = json.loads(old_path.read_text()) if old_path.exists() else {}
    previous = {e['id']: e for e in old.get('exports', [])}
    cache_path=ROOT/'.local/website/portrait-cache.json'
    cache=json.loads(cache_path.read_text()) if cache_path.exists() else {}
    inputs=renderer_inputs()
    def current(task):
        return any(reusable(task,entry,directory/(task['id']+'.webp'),inputs) for entry in (cache.get(task['id'],{}),previous.get(task['id'],{})))
    all_pending = [t for t in tasks if args.force or not current(t)]
    pending = all_pending
    if args.character:
        known = {t['character'] for t in tasks}
        if set(args.character)-known:
            parser.error('Unknown character ID')
        pending = [t for t in pending if t['character'] in args.character]
    if args.pose:
        pending = [t for t in pending if t['pose'] in args.pose]
    if args.check:
        if all_pending or manifest()!=old:
            raise SystemExit(f'{len(all_pending)} portraits require a website build')
        inventory_path=directory/'inventory.json'
        current_inventory=json.loads(inventory_path.read_text())
        expected_inventory=audit()
        expected_inventory['inventory_date']=current_inventory.get('inventory_date')
        if current_inventory != expected_inventory:
            raise SystemExit('Restoration status and completion statistics are stale')
        for name, content in legal_outputs().items():
            if (ROOT/name).read_text()!=content:
                raise SystemExit('Legal page is stale: '+name)
        snapshot=ROOT/'resources/site-manifest.json'
        if not snapshot.is_file() or json.loads(snapshot.read_text())!=site_manifest(ROOT):
            raise SystemExit('Download availability snapshot is stale')
        report=delivery(ROOT,args.output,check=True)
        print(f"Verified {len(tasks)} portraits, all restoration statistics and {report['file_count']} delivered files in {time.perf_counter()-started:.2f}s")
        return
    timings['planning_seconds']=round(time.perf_counter()-started,3)
    rendering_started=time.perf_counter()
    if pending:
        if not args.ffdec or not Path(args.ffdec).is_file():
            parser.error('Rendering needs --ffdec /path/to/ffdec.jar (or FFDEC_JAR)')
        with tempfile.TemporaryDirectory(prefix='boufbowl-site-') as temporary:
            temporary = Path(temporary)
            source = startup_source((ROOT/'patches/StartUpApplicationCommand.as').read_text(), load_config())
            marker = 'createToolbar();'
            if marker not in source:
                raise RuntimeError('Capture injection point is missing')
            source = source.replace(marker, marker+'\n'+(ROOT/'tools/site_portrait_capture.as.inc').read_text(), 1)
            startup = temporary/'StartUpApplicationCommand.as'
            startup.write_text(source)
            capture = temporary/'capture.swf'
            capture_key=hashlib.sha256(source.encode()+(ROOT/'bin/boufbowl-client-1.9.6.swf').read_bytes()+Path(args.ffdec).read_bytes()).hexdigest()
            capture_cache=ROOT/'.local/website/capture'/f'{capture_key}.swf'
            if capture_cache.is_file():
                shutil.copyfile(capture_cache,capture)
                print('Reusing compiled capture SWF',flush=True)
            else:
                subprocess.run([args.java,'-jar',str(Path(args.ffdec).resolve()),'-replace',
                    str(ROOT/'bin/boufbowl-client-1.9.6.swf'),str(capture),
                    'com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand',str(startup)],check=True,timeout=180)
                capture_cache.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(capture,capture_cache.with_suffix('.building.swf'))
                capture_cache.with_suffix('.building.swf').replace(capture_cache)
            token = '/build-'+secrets.token_hex(16)
            ids = {t['id'] for t in pending}
            batches={}
            for task in pending:batches.setdefault(task['character'],[]).append(task)
            queue=deque(batches.values())
            lock=threading.Lock()
            completed=set()
            html = '''<!doctype html><script src="/vendor/ruffle/ruffle.js"></script><div id="mount"></div><script type="module">
import {createPortraitPlayer,capturePortrait} from '/tools/site_portrait_capture.js';
const result={done:0,errors:[],characters:[]};
try {
const p=await createPortraitPlayer(document.querySelector('#mount'),'/bin/site-portraits.swf');
while(true){const tasks=await(await fetch(location.pathname+'/next')).json();if(!tasks.length)break;
result.characters.push(tasks[0].character);
for(const task of tasks){
const capture=await capturePortrait(p,task);
const response=await fetch(location.pathname+'/'+task.id,{method:'POST',body:capture.blob});
if(!response.ok)throw Error(await response.text());result.done++;
}}
result.character_initializations=p.ruffle().callExternalInterface('siteCharacterInitializations');
if(result.character_initializations!==result.characters.length)throw Error('Character initialization was not reused');
}catch(error){result.errors.push(String(error));}window.result=result;
</script>'''
            class Handler(SimpleHTTPRequestHandler):
                def __init__(self,*a,**kw):
                    super().__init__(*a,directory=str(ROOT),**kw)
                def log_message(self,*a):
                    pass
                def do_GET(self):
                    if self.path == token+'/next':
                        with lock:batch=queue.popleft() if queue else []
                        self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps(batch).encode())
                    elif self.path == token:
                        data=html.encode();self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(data)
                    elif self.path == '/bin/site-portraits.swf':
                        self.send_response(200);self.end_headers();self.wfile.write(capture.read_bytes())
                    elif self.path.startswith(('/assets/','/resources/','/vendor/','/tools/site_portrait_capture.js')):
                        super().do_GET()
                    else:
                        self.send_error(404)
                def do_POST(self):
                    identity=self.path.removeprefix(token+'/')
                    if identity not in ids:
                        self.send_error(404);return
                    try:
                        size=int(self.headers.get('Content-Length','0'))
                        if not 0<size<8000000:raise ValueError('Invalid upload size')
                        payload=self.rfile.read(size)
                        output=directory/(identity+'.webp');staging=temporary/(identity+'.webp')
                        staging.write_bytes(payload)
                        width,height=webp_size(staging)
                        if height!=1080 or not 80<width<8000:raise ValueError('Invalid dimensions')
                        shutil.copyfile(staging, output.with_suffix('.building.webp'))
                        output.with_suffix('.building.webp').replace(output)
                        task=next(t for t in pending if t['id']==identity)
                        with lock:
                            if identity in completed:raise ValueError('Duplicate export')
                            completed.add(identity)
                            cache[identity]={**task,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'render_fingerprint':render_fingerprint(task,inputs)}
                            write_json(cache_path,cache)
                        print(f'Rendered {identity} ({len(completed)}/{len(pending)})',flush=True)
                        self.send_response(200);self.end_headers()
                    except Exception as error:
                        self.send_error(500,str(error))
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                subprocess.run([args.bun,str(ROOT/'tools/website/render.mjs'),f'http://127.0.0.1:{server.server_port}{token}',str(min(args.jobs,len(batches))),str(temporary/'render-report.json')],check=True,timeout=7200)
                if completed != ids:raise RuntimeError('Renderer did not complete every requested portrait')
                timings['workers']=json.loads((temporary/'render-report.json').read_text())
            finally:
                server.shutdown();server.server_close();thread.join()
    if renderer_inputs()!=inputs or export_plan(audit()['characters'],json.loads((ROOT/'resources/palettes.json').read_text()))!=tasks:
        raise RuntimeError('Rendering inputs changed during the build; rerun to refresh affected exports')
    timings['rendering_seconds']=round(time.perf_counter()-rendering_started,3)
    inventory_started=time.perf_counter()
    data=manifest()
    old_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    inventory=audit()
    write_json(directory/'inventory.json',inventory)
    for name, content in legal_outputs().items():
        (ROOT/name).write_text(content)
    write_json(ROOT/'resources/site-manifest.json',site_manifest(ROOT))
    timings['inventory_seconds']=round(time.perf_counter()-inventory_started,3)
    delivery_started=time.perf_counter()
    report=delivery(ROOT,args.output)
    timings['delivery_seconds']=round(time.perf_counter()-delivery_started,3)
    timings['total_seconds']=round(time.perf_counter()-started,3)
    write_json(ROOT/'.local/website/build-report.json',{
        'timings':timings,'portraits_rendered':len(pending),'portraits_total':len(tasks),
        'completion':inventory['summary'],'asset_groups':inventory['asset_groups'],
        'delivery':{'directory':str(args.output.resolve()),'file_count':report['file_count'],'bytes':report['bytes']}})
    print(f"Website ready: {len(tasks)} portraits; {len(pending)} rendered; {inventory['summary']['completion_percent']}% of catalogued assets found.")
    print(f"Delivered {report['file_count']} files ({report['bytes']/1024/1024:.1f} MiB) to {args.output}")
    print('Timing: '+', '.join(f'{key}={value:.3f}' for key,value in timings.items() if isinstance(value,(int,float))))


if __name__=='__main__':
    execution_started = time.perf_counter()
    try:
        main()
    finally:
        elapsed = time.perf_counter() - execution_started
        minutes, seconds = divmod(elapsed, 60)
        print(f'Total execution time: {int(minutes)} min {seconds:06.3f} s', flush=True)
