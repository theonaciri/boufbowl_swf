"""Export five native Tiphon character animations as 530 px, 30 fps website loops."""
import argparse
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import shutil
import subprocess
import threading

from tools.media_fingerprints import renderer_fingerprint, digest, file_hash, read_json
from tools.game_config import load_config, startup_source
from tools.build_tools import BuildError, ffdec_jar, java_binary
from tools.site_portraits import ROOT, export_plan
from tools.site_delivery import write_json

ANIMATIONS = [
    ('cra-1', 'AnimCourseNormale', 'Course'),
    ('cra-2', 'AnimStatiqueAir', 'Préparation · Air'),
    ('enutrof-2', 'AnimStatiqueTerre', 'Préparation · Terre'),
    ('eniripsa-2', 'AnimEsquive', 'Esquive'),
    ('iop-1', 'AnimLancer', 'Lancer'),
]
OUTPUT_FPS = 30


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java', default=shutil.which('java'))
    parser.add_argument('--ffdec', type=Path)
    parser.add_argument('--bun', default=shutil.which('bun'))
    parser.add_argument('--character', action='append', choices=[item[0] for item in ANIMATIONS],
                        help='Re-export only this character, preserving the other exports')
    args = parser.parse_args()
    if not args.bun:
        parser.error('Bun is required')
    work = ROOT/'.local/puppet-videos'
    work.mkdir(parents=True, exist_ok=True)
    output = ROOT/'assets/site/restoration/puppets'
    output.mkdir(parents=True, exist_ok=True)
    inventory = json.loads((ROOT/'assets/site/restoration/inventory.json').read_text())
    plans = export_plan(inventory['characters'], json.loads((ROOT/'resources/palettes.json').read_text()))
    tasks = []
    for character, animation, label in ANIMATIONS:
        if args.character and character not in args.character:
            continue
        palette = next(t for t in plans if t['character']==character)
        tasks.append({**{k: palette[k] for k in ('character','cls','gender','colors')},
                      'animation':animation, 'label':label, 'id':character+'-'+animation.lower()})
    dependencies = renderer_fingerprint(ROOT, ['tools/site_puppet_capture.as.inc', 'tools/website/puppet-videos.mjs'])
    manifest_path = output/'videos.json'
    previous = read_json(manifest_path, {}).get('exports', [])
    exports = {item['character']: item for item in previous}
    encoding = {'fps': OUTPUT_FPS, 'height': 530, 'codec': 'libsvtav1', 'crf': 35, 'preset': 8, 'recipe': file_hash(__file__)}
    pending = []
    capture_pending = []
    for task in tasks:
        task['fingerprint'] = digest({'task': task, 'renderer': dependencies})
        old = exports.get(task['character'], {})
        video = ROOT/old.get('path', 'missing')
        if (old.get('fingerprint') == task['fingerprint'] and old.get('encoding') == encoding
                and video.is_file() and old.get('sha256') == file_hash(video)):
            print('Reusing encoded', task['id'], flush=True)
            continue
        pending.append(task)
        folder = work/task['id']
        saved = read_json(folder/'capture.json', {})
        images = sorted(folder.glob('[0-9][0-9][0-9][0-9].png'))
        if (saved.get('fingerprint') != task['fingerprint'] or len(images) != saved.get('frames') or not images
                or saved.get('images') != {p.name: file_hash(p) for p in images}):
            capture_pending.append(task)
    if not pending:
        return
    (work/'tasks.json').write_text(json.dumps(capture_pending))
    if capture_pending:
        try:
            java = java_binary(args.java)
            ffdec = ffdec_jar(args.ffdec)
        except BuildError as error:
            parser.error(str(error))
        source = startup_source((ROOT/'patches/StartUpApplicationCommand.as').read_text(), load_config())
        source = source.replace('createToolbar();', 'createToolbar();\n'+(ROOT/'tools/site_puppet_capture.as.inc').read_text(), 1)
        startup = work/'StartUpApplicationCommand.as'
        startup.write_text(source)
        capture = work/'capture.swf'
        fingerprint = hashlib.sha256(source.encode()+(ROOT/'bin/boufbowl-client-1.9.6.swf').read_bytes()).hexdigest()
        stamp = work/'capture.sha256'
        if not capture.exists() or not stamp.exists() or stamp.read_text()!=fingerprint:
            subprocess.run([str(java), '-jar', str(ffdec), '-replace', str(ROOT/'bin/boufbowl-client-1.9.6.swf'),
                            str(capture), 'com.ankamagames.boufbowl.client.application.controller.StartUpApplicationCommand', str(startup)], check=True, timeout=180)
            stamp.write_text(fingerprint)

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(ROOT), **kw)
            def log_message(self, *a):
                pass
            def do_GET(self):
                if self.path=='/bin/site-puppets.swf':
                    data=capture.read_bytes()
                    self.send_response(200); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
                elif self.path=='/capture.html':
                    self.send_response(200); self.end_headers(); self.wfile.write(b'<!doctype html><script src="/vendor/ruffle/ruffle.js"></script><div id="mount"></div>')
                else:
                    super().do_GET()
        server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            subprocess.run([args.bun, str(ROOT/'tools/website/puppet-videos.mjs'),
                            f'http://127.0.0.1:{server.server_port}/capture.html', str(work)],check=True,timeout=900)
        finally:
            server.shutdown(); server.server_close(); thread.join()
    metadata = [read_json(work/task['id']/'capture.json') for task in pending]
    # Every original bone library declares 25 fps. Resample to 30 without changing playback speed.
    native_fps = int.from_bytes((ROOT/'assets/sprites/bones/0-deplacement.swl').read_bytes()[2:6], 'big')
    for task in metadata:
        count = task['frames']
        repeats = max(1, math.ceil(native_fps*2/count))
        while (count*repeats*OUTPUT_FPS) % native_fps:
            repeats += 1
        video = output/(task['id']+'.mp4')
        temporary = video.with_suffix('.building.mp4')
        subprocess.run(['ffmpeg','-y','-v','error','-framerate',str(native_fps),'-i',str(work/task['id']/'%04d.png'),
                        '-vf',f'loop=loop=-1:size={count}:start=0,fps={OUTPUT_FPS},scale=-2:530,format=yuv420p',
                        '-frames:v',str(count*repeats*OUTPUT_FPS//native_fps),
                        '-c:v','libsvtav1','-crf','35','-preset','8','-movflags','+faststart','-an',str(temporary)],check=True)
        temporary.replace(video)
        task.pop('images', None)
        task.update(path=video.relative_to(ROOT).as_posix(), width=454,height=530,fps=OUTPUT_FPS,native_fps=native_fps,
                    native_frames=count,cycles=repeats,seconds=count*repeats/native_fps,
                    codec='av1',crf=35,encoding=encoding,
                    sha256=hashlib.sha256(video.read_bytes()).hexdigest())
        exports[task['character']] = task
        write_json(manifest_path, {'renderer':'Original Tiphon/BoufbowlerSprite', 'exports':[exports[c] for c, _, _ in ANIMATIONS if c in exports]})
        print('Exported', task['id'], task['seconds'], 'seconds, 454 × 530 AV1 CRF 35, 30 fps',flush=True)
    exports.update({item['character']: item for item in metadata})
    complete = [exports[character] for character, _, _ in ANIMATIONS if character in exports]
    write_json(manifest_path, {'renderer':'Original Tiphon/BoufbowlerSprite', 'exports':complete})
    # Remove obsolete poster images after replacing the video exports.
    current_ids = {item['id'] for item in complete}
    for old in previous:
        if old['character'] in {item['character'] for item in metadata} and old['id'] not in current_ids:
            for extension in ('.mp4', '.webp'):
                (output/(old['id']+extension)).unlink(missing_ok=True)
    for poster in output.glob('*.webp'):
        poster.unlink()


if __name__=='__main__':
    main()
