"""Native community UI, persistent friendship, private messages and saved replay smoke."""
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
    if not os.environ.get('DISPLAY'): raise RuntimeError('Run under Xvfb')
    cfg=load_config();cfg['rules']['match'].update(turns_per_match=2,turns_per_period=2,placement_seconds=3,planning_seconds=3)
    evidence=ROOT/'evidence';data=Path(os.environ.get('BOUFBOWL_SMOKE_DATA',Path.home()/'.cache/boufbowl-live-smoke'))
    with tempfile.TemporaryDirectory(prefix='boufbowl-community-smoke-') as tmp:
        root=Path(tmp);state=root/'state';service=Service(root/'state.sqlite',cfg)
        class QuietHandler(Handler):
            def log_message(self,*args): pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)));server.service=service
        threading.Thread(target=server.serve_forever,daemon=True).start()
        bob=service.hello({'nickname':'NativeFriend','clubs':[initial_club()]})
        before=windows();env=dict(os.environ,XDG_DATA_HOME=str(data),XDG_STATE_HOME=str(state))
        log=(evidence/'community-launch.log').open('w')
        process=subprocess.Popen([sys.executable,str(ROOT/'play.py'),'--mode','server','--scene-3d','--profile','Community'+str(int(time.time())),
                                  '--server-url',f'http://127.0.0.1:{server.server_port}'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        trace=state/'boufbowl-tutorial/mock.log'
        saved=None
        try:
            wait_for(lambda:trace.exists() and 'Incoming CLUB_INFORMATION' in trace.read_text());wait_for(lambda:bool(windows()-before))
            window=sorted(windows()-before)[-1];time.sleep(1)
            alice=service.store.db.execute("SELECT id,nickname FROM profiles WHERE nickname<>'NativeFriend'").fetchone()
            fast=bool(os.environ.get('BOUFBOWL_COMMUNITY_FAST'))
            if fast:
                # Seed complete history without sending stale match events to this native client.
                with service.store.transaction():
                    cursor=service.store.db.execute('SELECT COALESCE(MAX(seq),0) FROM events').fetchone()[0]
                    seeded=service.create_match(alice['id'],None,1)
                    service.finish_placement(seeded)
                    for _ in (1,2):
                        service.resolve(seeded);service.store.save_match(seeded)
                        service.advance(seeded);service.store.save_match(seeded)
                    service.store.db.execute('DELETE FROM events WHERE profile_id=? AND seq>?',(alice['id'],cursor))
                    service.chat_configuration(alice['id']);service.emit_ranking(alice['id'])
            else:
                click(window,650,30);time.sleep(.4);click(window,380,255)
                wait_for(lambda:service.store.db.execute('SELECT COUNT(*) FROM match_results').fetchone()[0]==1,150)
                wait_for(lambda:'Incoming MATCH_END' in trace.read_text());time.sleep(1)
            click(window,715,30);time.sleep(.4)  # Home
            click(window,995,30);time.sleep(.4);click(window,200,350);time.sleep(.5)
            # Dialog y=95, stage-to-window y=30, x=20.
            type_text(window,250,435,'NativeFriend');click(window,175,475)
            wait_for(lambda:service.store.db.execute("SELECT COUNT(*) FROM friendships WHERE status='pending'").fetchone()[0]==1)
            service.community({'session':bob['session'],'action':'friend','verb':'accept','nickname':alice['nickname']})
            click(window,800,435);time.sleep(.5)
            subprocess.run(['import','-window','root',str(evidence/'community-friends.png')],check=True)
            click(window,650,175);time.sleep(.4)  # Messages tab
            type_text(window,250,435,'NativeFriend');click(window,800,435);time.sleep(.4)
            type_text(window,250,475,'A saved private message');click(window,800,475)
            wait_for(lambda:service.store.db.execute("SELECT COUNT(*) FROM chat_messages WHERE message='A saved private message'").fetchone()[0]==1)
            click(window,275,175);time.sleep(.4)  # Rankings tab
            subprocess.run(['import','-window','root',str(evidence/'community-rankings.png')],check=True)
            click(window,775,175);time.sleep(.4)  # Channels tab
            type_text(window,250,435,'fr,en');click(window,200,475)
            wait_for(lambda:service.store.db.execute('SELECT COUNT(*) FROM chat_subscriptions WHERE profile_id=?',(alice['id'],)).fetchone()[0]==2)
            click(window,850,135);time.sleep(.3)
            type_text(window,800,124,'/part en');subprocess.run(['xdotool','key','Return'],check=True)
            wait_for(lambda:service.store.db.execute("SELECT COUNT(*) FROM chat_subscriptions WHERE profile_id=? AND language='en'",(alice['id'],)).fetchone()[0]==0)
            type_text(window,800,124,'/join en');subprocess.run(['xdotool','key','Return'],check=True)
            wait_for(lambda:service.store.db.execute("SELECT COUNT(*) FROM chat_subscriptions WHERE profile_id=? AND language='en'",(alice['id'],)).fetchone()[0]==1)
            click(window,995,30);time.sleep(.4);click(window,200,350);time.sleep(.4)
            click(window,400,175);time.sleep(.4)  # History tab
            if not fast:
                type_text(window,250,435,'1');click(window,210,475)
                wait_for(lambda:trace.read_text().count('Outgoing ResolutionDoneMessage')>=4,150)
                wait_for(lambda:'Fixture delivered' in trace.read_text(),30)
                if service.store.db.execute('SELECT COUNT(*) FROM match_results').fetchone()[0]!=1: raise RuntimeError('Replay changed results')
                if 'ERROR ' in trace.read_text(): raise RuntimeError(trace.read_text())
                subprocess.run(['import','-window','root',str(evidence/'community-replay-result.png')],check=True)
            # Save through Flash's FileReference dialog, then spectate another player.
            click(window,715,30);time.sleep(.4)
            click(window,995,30);time.sleep(.4);click(window,200,350);time.sleep(.4)
            click(window,400,175);time.sleep(.4);type_text(window,250,435,'1');click(window,350,475);time.sleep(.5)
            click(window,220,245);time.sleep(1)
            saved=ROOT/'bin'/('community-replay-smoke-'+str(time.time_ns())+'.json')
            visible=subprocess.run(['xdotool','search','--onlyvisible','--name','.*'],capture_output=True,text=True,check=True).stdout.split()
            chooser=None
            for candidate in visible:
                geometry=subprocess.run(['xdotool','getwindowgeometry','--shell',candidate],capture_output=True,text=True).stdout
                dimensions=dict(line.split('=',1) for line in geometry.splitlines() if '=' in line)
                if 540<=int(dimensions.get('WIDTH',0))<=600 and 380<=int(dimensions.get('HEIGHT',0))<=450:
                    chooser=candidate;break
            subprocess.run(['import','-window','root',str(evidence/'community-save-dialog.png')],check=True)
            if chooser is None: raise RuntimeError('Cannot find native file chooser: '+str(visible))
            subprocess.run(['xdotool','windowfocus',chooser,'mousemove','--window',chooser,'300','303','click','1','key','Home','key','shift+End','key','BackSpace'],check=True)
            subprocess.run(['xdotool','type','--clearmodifiers',saved.name],check=True)
            subprocess.run(['xdotool','key','Return'],check=True)
            wait_for(saved.exists,30)
            payload=json.loads(saved.read_text())
            if not payload['completed'] or len(payload['records'])!=2: raise RuntimeError('Saved replay incomplete')
            (evidence/'community-saved-replay.json').write_text(saved.read_text())
            click(window,850,190);time.sleep(.3)  # Close save-ready dialog
            previous_ends=trace.read_text().count('Incoming MATCH_END')
            # Keep a long placement deadline so the watcher can join before resolution.
            with service.store.transaction():
                live=service.create_match(service.store.authenticate(bob['session']),None,1)
                live['deadline']=time.time()+15;service.store.save_match(live)
            click(window,995,30);time.sleep(.4);click(window,200,350);time.sleep(.4)
            click(window,525,175);time.sleep(.4);type_text(window,250,435,str(live['id']));click(window,220,475)
            wait_for(lambda:service.spectator_match(alice['id']) is not None)
            subprocess.run(['import','-window','root',str(evidence/'community-spectating.png')],check=True)
            acknowledgements=trace.read_text().count('Outgoing ResolutionDoneMessage')
            for turn in (1,2):
                wait_for(lambda:trace.read_text().count('Outgoing ResolutionDoneMessage')>=acknowledgements+turn,120)
                current=service.store.match(live['id'])
                if current['phase']!='resolution' or current['turn']!=turn: raise RuntimeError('Spectator advanced authority')
                # The owner acknowledges only after the native watcher finishes its animation.
                service.command({'session':bob['session'],'request_id':'watch-owner-'+str(turn),
                                 'hex':service.codec.envelope('RESOLUTION_DONE',{'turn':turn}).hex()})
            wait_for(lambda:service.store.db.execute('SELECT COUNT(*) FROM match_results').fetchone()[0]==2,30)
            wait_for(lambda:trace.read_text().count('Incoming MATCH_END')>previous_ends,30)
            if 'ERROR ' in trace.read_text(): raise RuntimeError(trace.read_text())
            print('Native friends, messages, rankings, languages, JSON file saving and live spectator animations/acknowledgement isolation verified.' if fast else 'Native friends, messages, rankings, languages, saved replay, JSON file saving and live spectating verified; replay rewards unchanged.')
        finally:
            if saved is not None: saved.unlink(missing_ok=True)
            if trace.exists(): (evidence/'community-trace.log').write_text(trace.read_text())
            wineserver=shutil.which('wineserver') or '/usr/lib/x86_64-linux-gnu/wine/wineserver'
            subprocess.run([wineserver,'-k'],env=dict(env,WINEPREFIX=str(data/'boufbowl-tutorial/wine')),check=False)
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
            log.close();server.shutdown();server.server_close();service.close()


if __name__=='__main__':main()
