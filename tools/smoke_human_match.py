"""Native two-client account login, matchmaking, replay and result regression."""
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
from tools.build_mock_fixture import build_fixture
from tools.game_config import ROOT,load_config


def initial_club():
    roster=build_fixture()['steps'][0]['decoded']['leftRoster']
    return {'clubId':'1','clubName':'Human Smoke','boufbowler':roster['characters'],'paletteId':1,
            'firstColor':roster['firstColor'],'secondColor':roster['secondColor'],'patternColor':roster['patternColor'],
            'sigilBackground':1,'sigilCharge':1,'isPredefinedClub':False}


def windows():
    result=subprocess.run(['xdotool','search','--onlyvisible','--name','Adobe Flash Player'],capture_output=True,text=True)
    return set(result.stdout.split())


def click(window,x,y):
    subprocess.run(['xdotool','windowraise',window,'windowfocus',window,'mousemove','--window',window,str(x),str(y),'click','1'],check=True)


def type_text(window,x,y,text):
    click(window,x,y)
    subprocess.run(['xdotool','key','ctrl+a'],check=True)
    subprocess.run(['xdotool','type','--clearmodifiers',text],check=True)


def wait_for(predicate,seconds=60):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.25)
    raise RuntimeError('Native smoke timed out')


def main():
    if not os.environ.get('DISPLAY'):raise RuntimeError('Run under Xvfb with a 1280x800 display')
    cfg=load_config();cfg['rules']['match'].update(turns_per_match=2,turns_per_period=2,placement_seconds=25,planning_seconds=5)
    evidence=ROOT/'evidence';evidence.mkdir(exist_ok=True)
    data=Path(os.environ.get('BOUFBOWL_SMOKE_DATA',Path.home()/'.cache/boufbowl-live-smoke'))
    processes=[];logs=[]
    with tempfile.TemporaryDirectory(prefix='boufbowl-human-smoke-') as temporary:
        root=Path(temporary);service=Service(root/'backend.sqlite',cfg)
        class QuietHandler(Handler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)));server.service=service
        threading.Thread(target=server.serve_forever,daemon=True).start()
        profiles=[]
        for username in ('nativealice','nativebob'):
            account=service.account({'action':'register','username':username,'password':'native-smoke-password',
                                     'nickname':username,'clubs':[initial_club()]})
            profiles.append(service.store.authenticate(account['session']))
        try:
            for index,username in enumerate(('nativealice','nativebob')):
                state=root/str(index);env=dict(os.environ,XDG_DATA_HOME=str(data),XDG_STATE_HOME=str(state))
                before=windows();log=(evidence/f'human-client-{index}-launch.log').open('w');logs.append(log)
                process=subprocess.Popen([sys.executable,str(ROOT/'play.py'),'--mode','server','--scene-3d',
                    '--profile',f'HumanDevice{index}-{int(time.time())}','--server-url',f'http://127.0.0.1:{server.server_port}'],
                    cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT);processes.append(process)
                trace=state/'boufbowl-tutorial/mock.log'
                wait_for(lambda:trace.exists() and 'Incoming CLUB_INFORMATION' in trace.read_text())
                wait_for(lambda:bool(windows()-before));window=sorted(windows()-before)[-1]
                time.sleep(1)
                click(window,995,30);time.sleep(.5)  # window-relative menu adds 30px, unlike root's 50px
                click(window,790,295);time.sleep(.5)
                type_text(window,330,225,username);type_text(window,330,265,'native-smoke-password')
                click(window,170,385)
                wait_for(lambda:trace.read_text().count('Incoming CLUB_INFORMATION')>=2)
                if index==0:
                    type_text(window,800,124,'Hello opponent')
                    subprocess.run(['xdotool','key','Return'],check=True)
                    wait_for(lambda:service.store.db.execute('SELECT COUNT(*) FROM chat_messages').fetchone()[0]==1)
                click(window,650,30);time.sleep(.5);click(window,180,255)
                if index==0:
                    wait_for(lambda:service.matchmaking_status(profiles[0])['status']=='waiting')
                else:
                    wait_for(lambda:service.store.active_match(profiles[1]) is not None)
            wait_for(lambda:service.store.db.execute('SELECT COUNT(*) FROM match_results').fetchone()[0]==2,180)
            time.sleep(2)
            match=service.store.active_match(profiles[0])
            if match is not None:raise RuntimeError('Human match did not end')
            for index in (0,1):
                trace=(root/str(index)/'boufbowl-tutorial/mock.log').read_text()
                for marker in ('Playback script built','Playback mode 3D','Outgoing ResolutionDoneMessage'):
                    if trace.count(marker)!=2:raise RuntimeError('Incomplete human trace: '+trace)
                if 'Incoming MATCH_END' not in trace or 'ERROR ' in trace:raise RuntimeError(trace)
                (evidence/f'human-client-{index}-trace.log').write_text(trace)
            subprocess.run(['import','-window','root',str(evidence/'human-match-result.png')],check=True)
            print('Two account logins, queued human pairing, two native turns each, four acknowledgements and two saved results verified.')
        finally:
            for index in (0,1):
                trace_path=root/str(index)/'boufbowl-tutorial/mock.log'
                if trace_path.exists(): (evidence/f'human-client-{index}-trace.log').write_text(trace_path.read_text())
            wineserver=shutil.which('wineserver') or '/usr/lib/x86_64-linux-gnu/wine/wineserver'
            subprocess.run([wineserver,'-k'],env=dict(os.environ,WINEPREFIX=str(data/'boufbowl-tutorial/wine')),check=False)
            for process in processes:
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
            for log in logs:log.close()
            server.shutdown();server.server_close();service.close()


if __name__=='__main__':main()
