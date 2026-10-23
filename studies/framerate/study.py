"""Isolated FPS diagnostic; never writes production patches or published artifacts."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.client_probe import compile_probe, probe_root, replace_once, ROOT_CLASS
from tools.game_config import ROOT


def build(production_policy=False):
    from tools.visual_assets import prepare_stadiums
    prepare_stadiums(ROOT)
    from tools.build_interaction_fixtures import fixture
    record=json.loads((ROOT/'studies/framerate/reception-record.json').read_text())
    generated=ROOT/'.local/framerate-study/reception.json'
    generated.parent.mkdir(parents=True,exist_ok=True)
    generated.write_text(json.dumps(fixture('reception',record),indent=2)+'\n')
    source=probe_root('desktop')
    source=replace_once(source,'this.initializeClientRuntime(true);','this.initializeClientRuntime(true);\n         this.initializeStudy();\n         if(loaderInfo.parameters.studyBare == \"1\") return;')
    if not production_policy:
        source=replace_once(source,'return ruffleRuntime ? browserFrameRate :\n','if(studyPolicyEnabled && studyRate > 0) return studyRate;\n         return ruffleRuntime ? browserFrameRate :\n')
    position=source.rfind('   }')
    source=source[:position]+(ROOT/'studies/framerate/probe.as.inc').read_text()+source[position:]
    changes=[(ROOT_CLASS,source)]
    for filename,marker,code in [
      ('SceneController.as','      public function update() : void\n      {','\n         com.ankamagames.boufbowl.BoufbowlClient.studyRecordScene();'),
      ('UIController.as','      public function update(gameTime:int, realTime:int) : void\n      {','\n         com.ankamagames.boufbowl.BoufbowlClient.studyUiUpdates++;'),
      ('MovieClipSpritePresenter.as','      public function set position(point:Point3) : void\n      {','\n         com.ankamagames.boufbowl.BoufbowlClient.studyPositionWrites++;')]:
        text=(ROOT/'patches'/filename).read_text()
        if filename=='UIController.as':
            import re
            match=re.search(r'      public function update\([^\n]+\) : void\n      \{',text)
            if not match: raise ValueError('UI update anchor missing')
            marker=match.group()
        text=replace_once(text,marker,marker+code)
        import re
        package=re.search(r'package ([^\s]+)',text).group(1)
        changes.append((package+'.'+filename[:-3],text))
    return compile_probe(ROOT/'bin/boufbowl-client-1.9.6.swf',changes)


def serve(client,port,production_policy=False):
    directory=client.parent
    results=ROOT/'studies/framerate/applied' if production_policy else ROOT/'studies/framerate'
    logs=ROOT/'.local/framerate-study/applied' if production_policy else ROOT/'.local/framerate-study'
    results.mkdir(parents=True,exist_ok=True)
    logs.mkdir(parents=True,exist_ok=True)
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self,*_): pass
        def do_GET(self):
            from urllib.parse import urlsplit,parse_qs
            path=urlsplit(self.path).path
            referer=self.headers.get('Referer','')
            rate=parse_qs(urlsplit(referer).query).get('fps',['none'])[0]
            files={'/study.html':ROOT/'studies/framerate/study.html','/client.swf':client,'/resources/mock_match.json':ROOT/'.local/framerate-study/reception.json'}
            if path in files:
                body=files[path].read_bytes();self.send_response(200)
                self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            elif path=='/progress':
                requested=parse_qs(urlsplit(self.path).query).get('fps',[''])[0]
                if not requested.isdigit():self.send_error(400);return
                log=logs/f'replay-{int(requested)}.jsonl'
                events=[json.loads(line)['event'] for line in log.read_text().splitlines()] if log.exists() else []
                body=json.dumps({'done':any('Incoming MATCH_END' in e for e in events),'events':events}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            elif path=='/__mock_trace':
                message=parse_qs(urlsplit(self.path).query).get('event',[''])[0]
                with (directory/'replay.log').open('a') as stream:stream.write(message+'\n')
                if rate.isdigit():
                    with (logs/f'replay-{int(rate)}.jsonl').open('a') as stream:
                        stream.write(json.dumps({'event':message,'referer':referer})+'\n')
                self.send_response(204);self.end_headers()
            else: super().do_GET()
        def do_POST(self):
            if self.path!='/results':self.send_error(404);return
            data=json.loads(self.rfile.read(min(int(self.headers['Content-Length']),1000000)))
            mode=data.get('environment',{}).get('mode','game-ui')
            if mode not in ('bare','game-ui','replay','forced'):self.send_error(400);return
            suffix='-'+str(int(data['environment']['target'])) if mode=='replay' else ''
            target=results/f'results-{mode}{suffix}.json'
            target.write_text(json.dumps(data,indent=2)+'\n')
            self.send_response(204);self.end_headers()
    print(json.dumps({'status':'serving','url':f'http://127.0.0.1:{port}/study.html','client':str(client),'replayLog':str(directory/'replay.log')}),flush=True)
    with ThreadingHTTPServer(('127.0.0.1',port),partial(Handler,directory=str(ROOT))) as server:server.serve_forever()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--serve',action='store_true');parser.add_argument('--port',type=int,default=9913)
    parser.add_argument('--production-policy',action='store_true',help='Test maintained scene policy without the diagnostic bypass; save results separately')
    args=parser.parse_args()
    client,reused=build(args.production_policy);print(json.dumps({'status':'compiled','reused':reused,'client':str(client)}),flush=True)
    if args.serve:serve(client,args.port,args.production_policy)
