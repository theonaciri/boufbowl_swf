"""Re-render homepage cinematics from Flash vectors with an unrepeated legendary cast."""
import argparse
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import threading
from tools.game_config import load_config, startup_source
from tools.site_portraits import ROOT, export_plan

# Eighteen legendary actors, each appearing in exactly one carousel movie.
CAST = [
    ('terre-terre', 'Illustration_Terre_Terre', [501,505]),
    ('terre-feu', 'Illustration_Terre_Feu', [502,503]),
    ('feu-terre', 'Illustration_Feu_Terre', [506,507]),
    ('lancer', 'Illustration_lancer', [508]),
    ('reception-ok-air', 'Illustration_reception_ok_Air', [510]),
    ('reception-ratee-air', 'Illustration_reception_ratee_Air', [512]),
    ('interception', 'Illustration_interception', [511]),
    ('touchdown', 'Illustration_touchdown', [509]),
    ('masque-reception', 'Illustration_reception_ok_Air', [504]),
    ('harebourg-lancer', 'Illustration_lancer', [513]),
    ('pan-diego-interception', 'Illustration_interception', [514]),
    ('ironman-touchdown', 'Illustration_touchdown', [515]),
    ('jack-reception-ratee', 'Illustration_reception_ratee_Air', [516]),
    ('armand-reception', 'Illustration_reception_ok_Air', [517]),
    ('skunk-lancer', 'Illustration_lancer', [518]),
]
VERSION = 'legends-v2'
POSTER_FRAME_OVERRIDES = {'feu-terre': 10}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene',action='append',choices=[c[0] for c in CAST])
    parser.add_argument('--capture-only',action='store_true')
    parser.add_argument('--encode-only',action='store_true')
    parser.add_argument('--force',action='store_true')
    args=parser.parse_args()
    work=ROOT/'.local/home-cinematics';work.mkdir(parents=True,exist_ok=True)
    output=ROOT/'assets/site'
    source=startup_source((ROOT/'patches/StartUpApplicationCommand.as').read_text(),load_config())
    source=source.replace('createToolbar();','createToolbar();\n'+(ROOT/'tools/site_cinematic_capture.as.inc').read_text(),1)
    startup=work/'StartUpApplicationCommand.as';startup.write_text(source)
    fingerprint=hashlib.sha256(source.encode()+(ROOT/'bin/boufbowl-client-1.9.6.swf').read_bytes()).hexdigest()
    capture=work/'capture.swf';stamp=work/'capture.sha256'
    if not capture.exists() or not stamp.exists() or stamp.read_text()!=fingerprint:
        cache=Path.home()/'.cache/boufbowl-flash-tools'
        java=shutil.which('java') or next(cache.glob('jdk-17/*/bin/java'))
        subprocess.run([str(java),'-jar',str(cache/'ffdec-26.3.0/ffdec.jar'),'-replace',str(ROOT/'bin/boufbowl-client-1.9.6.swf'),str(capture),'com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand',str(startup)],check=True,timeout=180)
        stamp.write_text(fingerprint)
    inventory=json.loads((ROOT/'assets/site/restoration/inventory.json').read_text())
    palette_plan=export_plan(inventory['characters'],json.loads((ROOT/'resources/palettes.json').read_text()))
    tasks=[]
    for slug,symbol,heroes in CAST:
        actors=[]
        for index,hero in enumerate(heroes):
            palette=next(t for t in palette_plan if t['hero']==hero)
            character=next(c for c in inventory['characters'] if c['hero']==hero)
            actors.append({'hero':hero,'name':character['name'],'cls':palette['cls'],'gender':palette['gender'],
                           **{k:int(v,16) for k,v in palette['colors'].items()},
                           'team':0 if hero==508 else (0x3578cf if index==0 else 0xd14b33)})
        task={'slug':slug,'name':symbol,'actors':actors,'width':2560,'height':1500,'native_fps':25,'fps':60,
              'base':f'cinematic-{slug}-{VERSION}'}
        task['fingerprint']=hashlib.sha256(json.dumps(task,sort_keys=True).encode()+fingerprint.encode()+(ROOT/'assets/artworks/cutscene-illustration.swf').read_bytes()+(ROOT/'tools/website/cinematics.mjs').read_bytes()).hexdigest()
        if args.scene and slug not in args.scene:continue
        tasks.append(task)
    assert len({a['hero'] for t in tasks for a in t['actors']})==sum(len(t['actors']) for t in tasks)
    plan=work/'plan.json';plan.write_text(json.dumps(tasks,ensure_ascii=False,indent=2))
    pending=[]
    for task in tasks:
        metadata=work/task['slug']/'capture.json'
        if args.force or not metadata.exists() or json.loads(metadata.read_text()).get('fingerprint')!=task['fingerprint']:
            pending.append(task)
    if pending and not args.encode_only:
        (work/'pending.json').write_text(json.dumps(pending))
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
            def log_message(self,*args):pass
            def do_GET(self):
                if self.path=='/bin/capture-home.swf':
                    data=capture.read_bytes();self.send_response(200);self.end_headers();self.wfile.write(data)
                elif self.path=='/capture.html':
                    self.send_response(200);self.end_headers();self.wfile.write(b'<!doctype html><style>html,body{margin:0;overflow:hidden}</style><script src="/vendor/ruffle/ruffle.js"></script><div id="mount"></div>')
                else:super().do_GET()
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            subprocess.run([shutil.which('bun'),str(ROOT/'tools/website/cinematics.mjs'),f'http://127.0.0.1:{server.server_port}/capture.html',str(work)],check=True,timeout=10800)
        finally:server.shutdown();server.server_close();thread.join()
    if args.capture_only:return
    for task in tasks:
        folder=work/task['slug'];metadata=json.loads((folder/'capture.json').read_text())
        if metadata['fingerprint']!=task['fingerprint']:raise ValueError('Stale capture: '+task['slug'])
        target=output/task['base'];av1=target.with_suffix('.av1.mp4');fallback=target.with_suffix('.mp4');avif=target.with_suffix('.avif');poster=target.with_suffix('.webp')
        native=folder/'native.mkv'
        prior=folder/'export.json'
        if not args.force and prior.exists():
            saved=json.loads(prior.read_text())
            if saved.get('fingerprint')==task['fingerprint'] and all((ROOT/e['path']).is_file() and (ROOT/e['path']).stat().st_size==e['bytes'] for e in saved.get('exports',{}).values()):
                print('Reusing encoded',task['slug'],flush=True)
                continue
        if task['slug'] in POSTER_FRAME_OVERRIDES:
            metadata['poster_frame']=POSTER_FRAME_OVERRIDES[task['slug']]
            subprocess.run(['ffmpeg','-y','-v','error','-ss',str((metadata['poster_frame']-1)/25),'-i',str(native),'-frames:v','1',str(folder/'poster.png')],check=True)
        print('Encoding',task['slug'],flush=True)
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(native),'-vf','fps=60,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p10le','-an','-c:v','libsvtav1','-preset','8','-crf','20','-svtav1-params','lp=3:film-grain=0','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart',str(av1)],check=True)
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(av1),'-map','0:v:0','-c:v','copy','-loop','0',str(avif)],check=True)
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(native),'-vf','fps=60,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p','-an','-c:v','libx264','-preset','fast','-crf','16','-threads','3','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-movflags','+faststart',str(fallback)],check=True)
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(folder/'poster.png'),'-frames:v','1','-c:v','libwebp','-quality','95',str(poster)],check=True)
        metadata['exports']={key:{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for key,p in [('avif',avif),('av1',av1),('h264',fallback),('poster',poster)]}
        (folder/'export.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
        print('Exported',task['slug'],flush=True)
    complete=[]
    for slug,_,_ in CAST:
        p=work/slug/'export.json'
        if p.exists():complete.append(json.loads(p.read_text()))
    (ROOT/'docs/site/media-sources.json').write_text(json.dumps({'version':2,'source':'assets/artworks/cutscene-illustration.swf','capture':'Original Flash vectors and native palettes, deterministic frame capture through Ruffle','clips':complete},ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
