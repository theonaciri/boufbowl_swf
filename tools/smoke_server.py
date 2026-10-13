"""Run under Xvfb: prove a complete live CPU match in the original 3D client."""
import json,os,shutil,subprocess,sys,tempfile,threading,time
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from backend.server import Handler
from backend.service import Service
from tools.game_config import ROOT,load_config


def main():
    if not os.environ.get('DISPLAY'): raise RuntimeError('Run under xvfb-run with a 1280x800 display')
    config=load_config();config['rules']['match'].update(turns_per_match=2,turns_per_period=2,placement_seconds=3,planning_seconds=3)
    evidence=ROOT/'evidence';evidence.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='boufbowl-server-smoke-') as temporary:
        state=Path(temporary)/'state';data=Path(os.environ.get('BOUFBOWL_SMOKE_DATA',Path.home()/'.cache/boufbowl-live-smoke'))
        service=Service(Path(temporary)/'backend.sqlite',config)
        class QuietHandler(Handler):
            def log_message(self,*args): pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)));server.service=service
        threading.Thread(target=server.serve_forever,daemon=True).start()
        env=dict(os.environ,XDG_DATA_HOME=str(data),XDG_STATE_HOME=str(state))
        with (evidence/'live-server-launch.log').open('w') as log:
            game=subprocess.Popen([sys.executable,str(ROOT/'play.py'),'--mode','server','--scene-3d','--profile','Smoke'+str(int(time.time())),
                 '--server-url',f'http://127.0.0.1:{server.server_port}'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            trace_path=state/'boufbowl-tutorial/mock.log'
            try:
                deadline=time.monotonic()+60
                while time.monotonic()<deadline:
                    if trace_path.exists() and 'Incoming CLUB_INFORMATION' in trace_path.read_text(): break
                    if game.poll() is not None: raise RuntimeError('Client exited during bootstrap')
                    time.sleep(.25)
                else: raise RuntimeError('Client did not connect within 60 seconds')
                time.sleep(1)
                subprocess.run(['xdotool','mousemove','650','60','click','1'],check=True)
                time.sleep(.5)
                subprocess.run(['xdotool','mousemove','380','290','click','1'],check=True)
                deadline=time.monotonic()+100;match=None
                while time.monotonic()<deadline:
                    with service.store.lock:
                        row=service.store.db.execute('SELECT state_json FROM matches ORDER BY id DESC LIMIT 1').fetchone()
                        match=json.loads(row[0]) if row else None
                    if match and match.get('phase')=='ended': break
                    if game.poll() is not None: raise RuntimeError('Client exited before match end')
                    time.sleep(.5)
                else: raise RuntimeError('Live match did not complete: '+str(match and match.get('phase')))
                time.sleep(1)
                trace=trace_path.read_text()
                for marker in ('Outgoing ResolutionDoneMessage','Playback script built','Playback mode 3D'):
                    if trace.count(marker)!=2: raise RuntimeError('Incomplete live trace: '+trace)
                if 'Incoming MATCH_END' not in trace or 'ERROR ' in trace: raise RuntimeError(trace)
                with service.store.lock:
                    count=service.store.db.execute('SELECT COUNT(*) FROM match_results').fetchone()[0]
                if count!=1: raise RuntimeError('Expected exactly one persisted human result')
                subprocess.run(['import','-window','root',str(evidence/'live-server-result.png')],check=True)
                (evidence/'live-server-trace.log').write_text(trace)
                print('Verified two live 3D turns, acknowledgements, match end and one persisted result.')
            finally:
                wineserver=shutil.which('wineserver') or '/usr/lib/x86_64-linux-gnu/wine/wineserver'
                subprocess.run([wineserver,'-k'],env=dict(env,WINEPREFIX=str(data/'boufbowl-tutorial/wine')),check=False)
                try: game.wait(timeout=10)
                except subprocess.TimeoutExpired: game.kill();game.wait()
                server.shutdown();server.server_close();service.close()


if __name__=='__main__':main()
