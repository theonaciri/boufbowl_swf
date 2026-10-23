"""A/B the real Away3D session without changing the live game or backend."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from studies.framerate.study import build,serve
from tools.build_tools import java_binary,ffdec_jar
from tools.client_probe import replace_once
from tools.game_config import ROOT

SESSION='away3d.core.session.SpriteSession'
CONTAINER='com.ankamagames.boufbowl.resolution.display.view.SceneContainer'
TIPHON='com.ankamagames.tiphon.display.TiphonSprite'

def exported():
    folder=ROOT/'.local/framerate-study/render-profile-sources'
    selected=[SESSION,CONTAINER,TIPHON]
    paths={name:folder/'scripts'/Path(name.replace('.','/')+'.as') for name in selected}
    stamp=folder/'source.sha256'
    source_hash=hashlib.sha256((ROOT/'bin/base/boufbowl-client-1.9.6.swf').read_bytes()).hexdigest()
    if not all(p.exists() for p in paths.values()) or not stamp.exists() or stamp.read_text()!=source_hash:
        folder.mkdir(parents=True,exist_ok=True)
        with (folder/'export.log').open('w') as log:
            subprocess.run([str(java_binary()),'-jar',str(ffdec_jar()),'-selectclass',','.join(selected),
                            '-export','script',str(folder),str(ROOT/'bin/base/boufbowl-client-1.9.6.swf')],stdout=log,stderr=subprocess.STDOUT,check=True)
        stamp.write_text(source_hash)
    return {name:p.read_text() for name,p in paths.items()}

def fixture():
    from backend.engine import Engine
    from tools.build_interaction_fixtures import fixture as make_fixture
    engine_config=ROOT/'backend/build/engine_base.json'
    engine_config.write_bytes((ROOT/'backend/engine_base.json').read_bytes())
    record=json.loads((ROOT/'studies/framerate/reception-record.json').read_text())
    world=deepcopy(record['initial'])
    for index,entity in enumerate(world['entities']):
        entity['position']={'q':-5 if index<5 else 5,'r':index%5-2}
        entity['stats']['agility']=100
        entity['status']['carrying_ball']=False
    world['ball'].update(position={'q':0,'r':4},holder_entity_id=None,in_flight=False)
    orders=[]
    for team in (0,1):
        selected=world['entities'][team*5:team*5+5]
        actions=[{'entity_id':e['id'],'action_type':'move','params':{'target_position':{'q':e['position']['q']+7,'r':e['position']['r']},'elements':{'TERRE':0,'FEU':0,'AIR':0,'EAU':0}}} for e in selected]
        orders.append({'player_id':str(team),'turn_number':1,'team_index':team,'nonce':'running'+str(team),'actions':actions})
    engine=Engine()
    try:result=engine.simulate(world,orders,1,12345,record['rules'],(False,False))
    finally:engine.close()
    record.update(initial=world,orders=result['orders'],result=result['result'])
    folder=ROOT/'.local/framerate-study/rendering';folder.mkdir(parents=True,exist_ok=True)
    path=folder/'ten-running.json'
    path.write_text(json.dumps(make_fixture('ten-running',record),indent=2)+'\n')
    (folder/'ten-running-record.json').write_text(json.dumps(record,indent=2)+'\n')
    return path

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',action='store_true');parser.add_argument('--serve',action='store_true');parser.add_argument('--port',type=int,default=9915)
    parser.add_argument('--reception',action='store_true',help='Use the saved pass/catch fixture instead of ten runners')
    args=parser.parse_args();sources=exported();changes=[]
    changes.append((SESSION,sources[SESSION] if args.baseline else (ROOT/'patches/SpriteSession.as').read_text()))
    container=replace_once(sources[CONTAINER],'this._view.render();','var renderStart:int=flash.utils.getTimer();\n               this._view.render();\n               com.ankamagames.boufbowl.BoufbowlClient.studyProfile("render",renderStart);')
    container=replace_once(container,'\n{','\n{\n   import flash.utils.getTimer;').replace('flash.utils.getTimer()','getTimer()')
    changes.append((CONTAINER,container))
    tiphon=replace_once(sources[TIPHON],'this.updateScale();\n      }\n      \n      public function boneChanged', 'var addedStart:int=flash.utils.getTimer();\n         this.updateScale();\n         com.ankamagames.boufbowl.BoufbowlClient.studyProfile("tiphonAdded",addedStart);\n      }\n      \n      public function boneChanged')
    tiphon=replace_once(tiphon,'\n{','\n{\n   import flash.utils.getTimer;').replace('flash.utils.getTimer()','getTimer()')
    changes.append((TIPHON,tiphon))
    client,reused=build(True,changes,(ROOT/'studies/framerate/render_probe.as.inc').read_text())
    mode='baseline' if args.baseline else 'retained'
    if args.reception:mode+='-reception'
    print(json.dumps({'status':'compiled','mode':mode,'client':str(client),'reused':reused}),flush=True)
    if args.serve:serve(client,args.port,True,ROOT/'studies/framerate/rendering'/mode,ROOT/'.local/framerate-study/rendering'/mode,
                        ROOT/'.local/framerate-study/reception.json' if args.reception else fixture())
