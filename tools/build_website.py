"""Generate website portraits from native Flash vectors, then refresh restoration data."""
import argparse
import base64
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import shutil
import struct
import subprocess
import tempfile
import threading
from tools.site_portraits import ROOT, POSES, export_plan, manifest, webp_size
from tools.game_config import load_config, startup_source
from tools.build_restoration_data import audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffdec', type=Path, default=os.environ.get('FFDEC_JAR'))
    parser.add_argument('--java', default=os.environ.get('JAVA', 'java'))
    parser.add_argument('--bun', default=os.environ.get('BUN', 'bun'))
    parser.add_argument('--pose', action='append', choices=list(POSES), help='Render only this pose (repeatable)')
    parser.add_argument('--character', action='append', help='Render only this character ID (repeatable)')
    parser.add_argument('--force', action='store_true', help='Re-render every portrait')
    parser.add_argument('--check', action='store_true', help='Verify existing exports without rendering')
    args = parser.parse_args()
    directory = ROOT/'assets/site/restoration'
    settings = json.loads((ROOT/'resources/palettes.json').read_text())
    tasks = export_plan(audit()['characters'], settings)
    old_path = directory/'portraits.json'
    old = json.loads(old_path.read_text()) if old_path.exists() else {}
    previous = {e['id']: e for e in old.get('exports', [])}
    sources_match = all(old.get(key) == hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for key,path in [
        ('source_sha256','assets/artworks/cutscene-boufbowler-repository.swf'),
        ('action_source_sha256','assets/artworks/cutscene-illustration.swf'),
        ('palettes_sha256','resources/palettes.json')])
    def current(task):
        path = directory/(task['id']+'.webp')
        entry = previous.get(task['id'], {})
        return (sources_match and all(entry.get(k)==v for k,v in task.items()) and path.is_file()
                and webp_size(path)[1]==1080 and entry.get('sha256')==hashlib.sha256(path.read_bytes()).hexdigest())
    pending = [t for t in tasks if args.force or not current(t)]
    if args.character:
        known = {t['character'] for t in tasks}
        if set(args.character)-known:
            parser.error('Unknown character ID')
        pending = [t for t in pending if t['character'] in args.character]
    if args.pose:
        pending = [t for t in pending if t['pose'] in args.pose]
    if args.check:
        if pending or manifest()!=old:
            raise SystemExit(f'{len(pending)} portraits require a website build')
        print(f'Verified {len(tasks)} portraits at 1080 px')
        return
    if pending:
        if not args.ffdec or not Path(args.ffdec).is_file():
            parser.error('Rendering needs --ffdec /path/to/ffdec.jar (or FFDEC_JAR)')
        if not shutil.which('ffmpeg'):
            parser.error('Rendering needs ffmpeg with libwebp')
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
            subprocess.run([args.java,'-jar',str(Path(args.ffdec).resolve()),'-replace',
                str(ROOT/'bin/boufbowl-client-1.9.6.swf'),str(capture),
                'com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand',str(startup)],check=True,timeout=180)
            token = '/build-'+secrets.token_hex(16)
            ids = {t['id'] for t in pending}
            html = '''<!doctype html><script src="/vendor/ruffle/ruffle.js"></script><div id="mount"></div><script type="module">
import {createPortraitPlayer,capturePortrait} from '/tools/site_portrait_capture.js';
const result={done:0,errors:[]};
try {
const tasks=TASKS;
const p=await createPortraitPlayer(document.querySelector('#mount'),'/bin/site-portraits.swf');
await new Promise(r=>setTimeout(r,3000));
for(const task of tasks){try{
const capture=await capturePortrait(p,task);
const response=await fetch(location.pathname+'/'+task.id,{method:'POST',body:capture.png});
if(!response.ok)throw Error(await response.text());result.done++;
}catch(error){result.errors.push({id:task.id,error:String(error)});break;}}
}catch(error){result.errors.push(String(error));}window.result=result;
</script>'''.replace('TASKS',json.dumps(pending))
            class Handler(SimpleHTTPRequestHandler):
                def __init__(self,*a,**kw):
                    super().__init__(*a,directory=str(ROOT),**kw)
                def log_message(self,*a):
                    pass
                def do_GET(self):
                    if self.path == token:
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
                        png=base64.b64decode(self.rfile.read(size),validate=True)
                        if png[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Invalid PNG')
                        width,height=struct.unpack('>II',png[16:24])
                        if height!=1080 or not 80<width<8000:raise ValueError('Invalid dimensions')
                        output=directory/(identity+'.webp');staging=temporary/(identity+'.webp')
                        subprocess.run(['ffmpeg','-y','-v','error','-i','pipe:0','-c:v','libwebp','-quality','92','-threads','1',str(staging)],input=png,check=True,timeout=60)
                        shutil.copyfile(staging, output.with_suffix('.building.webp'))
                        output.with_suffix('.building.webp').replace(output)
                        print('Rendered',identity,flush=True)
                        self.send_response(200);self.end_headers()
                    except Exception as error:
                        self.send_error(500,str(error))
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                subprocess.run([args.bun,str(ROOT/'tools/website/render.mjs'),f'http://127.0.0.1:{server.server_port}{token}'],check=True,timeout=7200)
            finally:
                server.shutdown();server.server_close();thread.join()
    data=manifest()
    old_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (directory/'inventory.json').write_text(json.dumps(audit(),ensure_ascii=False,indent=2)+'\n')
    print(f'Website ready: {len(tasks)} native portraits; {len(pending)} rendered.')


if __name__=='__main__':
    main()
