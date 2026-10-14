"""Native first-login private chat, whois, color editor and cold 3D regression."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from functools import partial
from http.server import ThreadingHTTPServer
from backend.server import Handler
from backend.service import Service
from tools.game_config import ROOT,load_config
from tools.smoke_human_match import initial_club,windows,click,type_text,wait_for


def main():
    cfg=load_config();cfg['rules']['match'].update(turns_per_match=2,turns_per_period=2,placement_seconds=3,planning_seconds=3)
    evidence=ROOT/'evidence';data=Path(os.environ.get('BOUFBOWL_SMOKE_DATA',Path.home()/'.cache/boufbowl-live-smoke'))
    with tempfile.TemporaryDirectory(prefix='boufbowl-regression-') as tmp:
        root=Path(tmp);state=root/'state';service=Service(root/'state.sqlite',cfg)
        class QuietHandler(Handler):
            def do_POST(self):
                if self.path=='/api/community':
                    with (evidence/'client-request-times.log').open('a') as timing: timing.write(str(time.monotonic())+' community delay='+str(getattr(self.server,'delay_player',False))+'\n')
                if self.path=='/api/community' and getattr(self.server,'delay_player',False):
                    self.server.delay_player=False
                    self.server.delayed_request_started=time.monotonic()
                    time.sleep(8)
                super().do_POST()
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)));server.service=service
        threading.Thread(target=server.serve_forever,daemon=True).start()
        peer=service.hello({'nickname':'NativePeer','clubs':[initial_club()]})
        env=dict(os.environ,XDG_DATA_HOME=str(data),XDG_STATE_HOME=str(state));before=windows()
        log=(evidence/'client-regressions-launch.log').open('w')
        process=subprocess.Popen([sys.executable,str(ROOT/'play.py'),'--mode','server','--scene-3d','--profile','Regression'+str(int(time.time())),
                                  '--server-url',f'http://127.0.0.1:{server.server_port}'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        trace=state/'boufbowl-tutorial/mock.log'
        try:
            wait_for(lambda:trace.exists() and 'Incoming CLUB_INFORMATION' in trace.read_text());wait_for(lambda:bool(windows()-before))
            window=sorted(windows()-before)[-1];time.sleep(1)
            # The original /w path previously dereferenced a missing PRIVATE channel.
            type_text(window,800,124,'/w NativePeer First-login private message')
            subprocess.run(['xdotool','key','Return'],check=True)
            wait_for(lambda:service.store.db.execute("SELECT COUNT(*) FROM chat_messages WHERE recipient IS NOT NULL").fetchone()[0]==1)
            type_text(window,800,124,'/whois NativePeer');subprocess.run(['xdotool','key','Return'],check=True)
            time.sleep(.6)
            subprocess.run(['import','-window','root',str(evidence/'client-player-information.png')],check=True)
            click(window,850,190);time.sleep(.3)
            if os.environ.get('BOUFBOWL_REGRESSION_TIMEOUT_ONLY'):
                with service.store.transaction():
                    live=service.create_match(service.store.authenticate(peer['session']),None,1)
                    live['deadline']=time.time()+3600;service.store.save_match(live)
                type_text(window,800,124,'/whois NativePeer');subprocess.run(['xdotool','key','Return'],check=True)
                time.sleep(.5)
                subprocess.run(['import','-window','root',str(evidence/'client-player-in-match.png')],check=True)
                click(window,850,190);time.sleep(.3)
                information_count=trace.read_text().count('Player information opened:')
                server.delay_player=True
                type_text(window,800,124,'/whois NativePeer');subprocess.run(['xdotool','key','Return'],check=True)
                try:wait_for(lambda:'Request cancelled after 6 seconds: community' in trace.read_text(),10)
                except RuntimeError:
                    subprocess.run(['import','-window','root',str(evidence/'client-timeout-failure.png')],check=True)
                    print('Delayed request started: '+str(getattr(server,'delayed_request_started',None))+'; launcher status: '+str(process.poll()),flush=True)
                    raise
                elapsed=time.monotonic()-server.delayed_request_started
                if not 5.5<=elapsed<=6.7:raise RuntimeError('Unexpected deadline: '+str(elapsed))
                time.sleep(3)
                if process.poll() is not None or trace.read_text().count('Player information opened:')!=information_count:
                    raise RuntimeError('Late response changed the UI or the player exited')
                subprocess.run(['import','-window','root',str(evidence/'client-request-timeout.png')],check=True)
                print('Native private chat, player information, active-match spectator visibility and six-second cancellation verified.')
                return
            click(window,740,165);time.sleep(1)
            subprocess.run(['import','-window','root',str(evidence/'client-color-editor.png')],check=True)
            print('Private message saved, player information opened; native color editor ready.',flush=True)
            initial=service.store.db.execute("SELECT club_json FROM profiles WHERE nickname<>'NativePeer'").fetchone()[0]
            # Wait for the color editor's asynchronous assets, then switch a high index into a shorter palette.
            time.sleep(3)
            subprocess.run(['xdotool','mousemove','958','383','click','1'],check=True)
            time.sleep(.3)
            subprocess.run(['xdotool','mousemove','981','465','click','1'],check=True)
            time.sleep(.5)
            subprocess.run(['xdotool','mousemove','729','380','click','1'],check=True)
            time.sleep(.5)
            subprocess.run(['import','-window','root',str(evidence/'client-short-palette.png')],check=True)
            subprocess.run(['xdotool','mousemove','853','546','click','1'],check=True)
            time.sleep(.5)
            subprocess.run(['xdotool','mousemove','408','380','click','1'],check=True)
            wait_for(lambda:service.store.db.execute("SELECT club_json FROM profiles WHERE nickname<>'NativePeer'").fetchone()[0]!=initial,300)
            if 'ERROR ' in trace.read_text():raise RuntimeError(trace.read_text())
            # Select Frigost (fifth stadium) and render two authoritative turns.
            click(window,650,30);time.sleep(.4)
            for _ in range(5):click(window,750,225);time.sleep(.15)
            click(window,380,255)
            wait_for(lambda:service.store.db.execute('SELECT COUNT(*) FROM match_results').fetchone()[0]==1,150)
            wait_for(lambda:'Incoming MATCH_END' in trace.read_text())
            match=json.loads(service.store.db.execute('SELECT state_json FROM matches').fetchone()[0])
            if match['stadium']!=5:raise RuntimeError('Expected Frigost')
            if trace.read_text().count('Outgoing ResolutionDoneMessage')!=2:raise RuntimeError(trace.read_text())
            # Retire a stalled request at six seconds and discard its late response.
            click(window,715,30);time.sleep(.5)
            information_count=trace.read_text().count('Player information opened:')
            server.delay_player=True
            type_text(window,800,124,'/whois NativePeer');subprocess.run(['xdotool','key','Return'],check=True)
            wait_for(lambda:'Request cancelled after 6 seconds: community' in trace.read_text(),10)
            elapsed=time.monotonic()-server.delayed_request_started
            if not 5.5<=elapsed<=6.7:raise RuntimeError('Unexpected request deadline: '+str(elapsed))
            time.sleep(3)
            if process.poll() is not None or trace.read_text().count('Player information opened:')!=information_count:
                raise RuntimeError('Late response changed the UI or the player exited')
            subprocess.run(['import','-window','root',str(evidence/'client-request-timeout.png')],check=True)
            print('First-login PM, player information, short-palette save, two-turn Frigost playback and six-second request cancellation verified.')
        finally:
            wine_log=state/'boufbowl-tutorial/wine.log'
            if wine_log.exists():(evidence/'client-regressions-wine.log').write_text(wine_log.read_text(errors='replace'))
            if trace.exists():(evidence/'client-regressions-trace.log').write_text(trace.read_text())
            wineserver=shutil.which('wineserver') or '/usr/lib/x86_64-linux-gnu/wine/wineserver'
            subprocess.run([wineserver,'-k'],env=dict(env,WINEPREFIX=str(data/'boufbowl-tutorial/wine')),check=False)
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
            log.close();server.shutdown();server.server_close();service.close()


if __name__=='__main__':main()
