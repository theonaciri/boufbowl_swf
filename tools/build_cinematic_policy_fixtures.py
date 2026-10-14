"""Build ball-cinematic probes, including cached replays with every flag enabled."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from backend.engine import Engine
from tools.build_interaction_fixtures import fixture
from tools.flash_protocol import Codec
from tools.game_config import ROOT


def build(output):
    output.mkdir(parents=True,exist_ok=True);codec=Codec()
    def save(name,record,cached=False):
        record['presentation']={'interactions':True}
        replay=fixture(name,record);scenario=replay['steps'][2]['decoded']
        if cached:
            # Model legacy saved flags so the native client guard is tested too.
            for entry in scenario['interaction']:entry['interactionDetails']['isCutscene']=True
            replay['steps'][2]['hex']=codec.envelope('RESOLUTION_SCENARIO',scenario).hex()
        (output/(name+'.json')).write_text(json.dumps(replay,indent=2)+'\n')
    combat=json.loads((ROOT/'tests/fixtures/interactions/combat-record.json').read_text())
    save('off-ball-cached',combat,True)
    engine=Engine()
    try:
        record=json.loads((ROOT/'tests/fixtures/interactions/reception-record.json').read_text())
        rules=deepcopy(record['rules']);rules['simulation']['simulation'].update(probability_min=1,probability_max=1)
        elements={'TERRE':0,'FEU':0,'AIR':2,'EAU':1}
        orders=deepcopy(record['orders'])
        positions={e['id']:e['position'] for e in record['initial']['entities']}
        orders[0]['actions']=[{'entity_id':actor,'action_type':'throw','params':{'target_entity_id':target,'target_position':positions[target],'elements':elements}} for actor,target in ((11,12),(12,11))]
        simulated=engine.simulate(record['initial'],orders,1,42,rules,(False,False))
        record.update(orders=simulated['orders'],result=simulated['result'],rules=rules)
        assert sum(e['type']=='throw' for e in record['result']['events'])==2
        save('two-passes-cached',record,True)
        world=deepcopy(combat['initial']);world['ball']['holder_entity_id']=11
        carrier=next(e for e in world['entities'] if e['id']==11)
        world['ball']['position']=deepcopy(carrier['position']);carrier['status']['carrying_ball']=True
        simulated=engine.simulate(world,combat['orders'],1,12345,combat['rules'],(False,False))
        combat.update(initial=world,orders=simulated['orders'],result=simulated['result'])
        save('carrier-fight',combat)
    finally:engine.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/boufbowl-ball-cinematics'))
    args=parser.parse_args();build(args.output);print(args.output)
