"""Native character palette, customization modes and matchmaking regression."""
import json,os,subprocess,sys,tempfile,time,threading,shutil
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from backend.service import Service
from backend.server import Handler
from tools.game_config import ROOT,load_config
from tools.smoke_human_match import windows,wait_for,click
def main():
    cfg=load_config();cfg['rules']['match'].update(turns_per_match=2,turns_per_period=2,placement_seconds=3,planning_seconds=3)
    with tempfile.TemporaryDirectory(prefix='boufbowl-color-probe-') as tmp:
     root=Path(tmp);service=Service(root/'state.sqlite',cfg)
     class QuietHandler(Handler):
      def log_message(self,*args):pass
     server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)));server.service=service
     threading.Thread(target=server.serve_forever,daemon=True).start()
     data=Path(os.environ.get('BOUFBOWL_SMOKE_DATA',Path.home()/'.cache/boufbowl-live-smoke'));env=dict(os.environ,XDG_DATA_HOME=str(data),XDG_STATE_HOME=str(root/'state'))
     before=windows();log=(ROOT/'evidence/color-probe-launch.log').open('w')
     process=subprocess.Popen([sys.executable,str(ROOT/'play.py'),'--mode','server','--profile','ColorProbe'+str(int(time.time())),'--server-url',f'http://127.0.0.1:{server.server_port}'],env=env,stdout=log,stderr=subprocess.STDOUT)
     trace=root/'state/boufbowl-tutorial/mock.log'
     try:
      wait_for(lambda:trace.exists() and 'Incoming CLUB_INFORMATION' in trace.read_text());wait_for(lambda:windows()-before)
      window=sorted(windows()-before)[-1];time.sleep(2)
      def root_click(x,y):
       subprocess.run(['xdotool','mousemove',str(x),str(y),'click','1'],check=True);time.sleep(.4)
      def capture(name):
       subprocess.run(['import','-window','root',str(ROOT/'evidence'/name)],check=True)
      def collection():
       return json.loads(service.store.db.execute('SELECT club_json FROM profiles').fetchone()[0])
      click(window,875,255);time.sleep(4)
      capture('character-appearance-editor.png')
      # Appearance must leave the class unchanged, including attempted class clicks.
      root_click(123,236)
      for x,y in ((908,616),(947,470),(868,470),(986,214),(720,340),
                  (986,214),(720,410),(986,214),(720,268),(986,214),(720,340)):
       root_click(x,y)
      capture('character-palette-switches.png')
      root_click(961,546);root_click(408,380)
      wait_for(lambda:collection()['clubs']['1']['boufbowler'][0]['paletteId']==101)
      assert collection()['clubs']['1']['boufbowler'][0]['boufbowlerClass']==1
      # Replacement opens the same editor with class selection enabled.
      root_click(925,285);time.sleep(3)
      root_click(123,236);root_click(250,180);time.sleep(1)
      capture('character-replacement-editor.png')
      root_click(961,546);root_click(408,380)
      wait_for(lambda:collection()['clubs']['1']['boufbowler'][0]['boufbowlerClass']!=1)
      # The original Home Play button must expose CPU, human and tournament controls.
      root_click(515,590);capture('home-matchmaking-options.png')
      root_click(740,458);root_click(380,299)
      wait_for(lambda:service.store.db.execute('SELECT COUNT(*) FROM matches').fetchone()[0]==1)
      match=json.loads(service.store.db.execute('SELECT state_json FROM matches').fetchone()[0])
      assert match['rosters'][0]['name']=='Offline Brakmar' and match['profiles'][1] is None
      assert collection()['active']=='2'
      wait_for(lambda:'Incoming MATCH_END' in trace.read_text(),150)
      root_click(635,60);time.sleep(.5);root_click(515,590);root_click(210,298)
      wait_for(lambda:service.store.db.execute('SELECT COUNT(*) FROM matchmaking_queue').fetchone()[0]==1)
      time.sleep(2)
      assert service.store.db.execute('SELECT COUNT(*) FROM matches').fetchone()[0]==1
      root_click(565,60);time.sleep(.4);root_click(550,298);time.sleep(.5)
      root_click(210,412)
      wait_for(lambda:service.store.db.execute('SELECT tournament_id FROM matchmaking_queue').fetchone()[0]=='1')
      assert service.store.db.execute('SELECT COUNT(*) FROM matches').fetchone()[0]==1
      from tools.smoke_human_match import initial_club
      peer=service.hello({'nickname':'TournamentPeer','clubs':[initial_club()]})
      service.command({'session':peer['session'],'request_id':'join','operation':'tournament_match','tournament_id':1})
      wait_for(lambda:service.store.db.execute('SELECT COUNT(*) FROM matches').fetchone()[0]==2)
      match=json.loads(service.store.db.execute('SELECT state_json FROM matches ORDER BY id DESC').fetchone()[0])
      assert match['tournament']==1 and all(match['profiles'])
      assert match['rosters'][0]['name']=='Offline Brakmar'
      capture('native-tournament-pairing.png')
      print('Native palette switching, appearance/replacement distinction, explicit team/CPU selection and human/tournament queues verified.',flush=True)

     finally:
      if trace.exists():(ROOT/'evidence/color-probe-trace.log').write_text(trace.read_text())
      wineserver=shutil.which('wineserver') or '/usr/lib/x86_64-linux-gnu/wine/wineserver'
      subprocess.run([wineserver,'-k'],env=dict(env,WINEPREFIX=str(data/'boufbowl-tutorial/wine')))
      process.wait(timeout=10);server.shutdown();server.server_close();service.close();log.close()


if __name__ == "__main__":
    main()
