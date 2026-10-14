"""Generate experimental-power playback probes without altering historical fixtures."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from backend.engine import Engine
from tools.build_interaction_fixtures import fixture
from tools.flash_protocol import Codec
from tools.game_config import ROOT, load_config
from tools.power_descriptions import NAMES


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    base=json.loads((ROOT/'tests/fixtures/interactions/ability-record.json').read_text())
    rules=load_config()['rules'];engine=Engine()
    try:
        for label,left,right in [('wounds','Sacrier','Rogue'),('masks','Zobal','Ecaflip'),('range','Cra','Sadida')]:
            world=deepcopy(base['initial']);entities={e['id']:e for e in world['entities']}
            entities[11]['class_name']=left;entities[21]['class_name']=right
            if left=='Zobal':entities[11]['zobal_mask']=1
            orders=[{'player_id':str(team),'turn_number':1,'team_index':team,'nonce':label,
                     'actions':[{'entity_id':identity,'action_type':'ability',
                                 'params':{'zobal_mask':2} if team==0 and left=='Zobal' else {}}]}
                    for team,identity in enumerate((11,21))]
            response=engine.simulate(world,orders,1,12345,rules,(False,False))
            record=dict(initial=world,orders=response['orders'],result=response['result'],rules=rules)
            probe=fixture(label,record);info=probe['steps'][0]['decoded']
            for roster in (info['leftRoster'],info['rightRoster']):
                for player in roster['characters']:
                    entity=entities.get(int(player['id']))
                    if entity:player['boufbowlerClass']=NAMES.index(entity['class_name'])+1
            probe['steps'][0]['hex']=Codec().envelope('MATCH_INFORMATION',info).hex()
            (args.output/(label+'.json')).write_text(json.dumps(probe,indent=2)+'\n')
            (args.output/(label+'-record.json')).write_text(json.dumps(record,indent=2)+'\n')
            print(label)
    finally:
        engine.close()


if __name__=='__main__':
    main()
