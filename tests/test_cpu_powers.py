from copy import deepcopy
import json
import unittest
from backend.engine import Engine
from tools.game_config import ROOT, load_config


class CPUPowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine=Engine();cls.rules=load_config()['rules']
        cls.base=json.loads((ROOT/'tests/fixtures/interactions/reception-record.json').read_text())['initial']

    @classmethod
    def tearDownClass(cls): cls.engine.close()

    def world(self,name='Rogue'):
        world=deepcopy(self.base)
        for e in world['entities']:
            e['class_name']=name if e['team_id']==0 else 'Iop'
            e['hp']=e['max_hp']=16;e['ability_uses_remaining']=2
            e['status']=dict(stunned=False,knocked_down=False,carrying_ball=False)
            e.pop('precise_position',None)
        world['ball'].update(holder_entity_id=None,in_flight=False,position={'q':0,'r':0})
        return world

    def run_cpu(self,world,rules=None,turn=1,orders=None):
        return self.engine.simulate(world,orders or [None,None],turn,12345,rules or self.rules,(True,False))

    def test_selects_one_power_and_removes_other_caster_actions(self):
        response=self.run_cpu(self.world())
        actions=response['orders'][0]['actions'];powers=[a for a in actions if a['action_type']=='ability']
        self.assertEqual(len(powers),1)
        self.assertEqual(len([a for a in actions if a['entity_id']==powers[0]['entity_id']]),1)
        self.assertTrue(any(e['type']=='ability' for e in response['result']['events']))
        world=response['result']['final_world_state']
        caster=next(e for e in world['entities'] if e['id']==powers[0]['entity_id'])
        self.assertEqual(caster['ability_uses_remaining'],1)
        self.assertEqual(response,self.run_cpu(self.world()))

    def test_does_not_cast_unavailable_powers(self):
        for reason in ('exhausted','stunned','knocked_down','dead'):
            world=self.world()
            for e in world['entities']:
                if e['team_id']!=0:continue
                if reason=='exhausted':e['ability_uses_remaining']=0
                elif reason=='dead':e['hp']=0
                else:e['status'][reason]=True
            with self.subTest(reason=reason):
                response=self.run_cpu(world)
                self.assertFalse(any(a['action_type']=='ability' for a in response['orders'][0]['actions']))

    def test_preserves_carrier_receiver_and_avoids_lethal_sacrifice(self):
        world=self.world();carrier=next(e for e in world['entities'] if e['id']==11)
        carrier['stats']['precision']=100;carrier['position']={'q':0,'r':0}
        receiver=next(e for e in world['entities'] if e['id']==12);receiver['position']={'q':5,'r':0};receiver['stats']['precision']=100
        world['ball'].update(holder_entity_id=11,position=carrier['position']);carrier['status']['carrying_ball']=True
        actions=self.run_cpu(world)['orders'][0]['actions']
        powers=[a['entity_id'] for a in actions if a['action_type']=='ability']
        self.assertNotIn(11,powers)
        for action in actions:
            if action['action_type']=='throw': self.assertNotIn(action['params']['target_entity_id'],powers)
        world=self.world('Sacrier');world['entities'][0]['hp']=1
        self.assertFalse(any(a['action_type']=='ability' for a in self.run_cpu(world)['orders'][0]['actions']))

    def test_heal_only_when_needed_and_replays_preserve_generated_orders(self):
        world=self.world('Eniripsa')
        self.assertFalse(any(a['action_type']=='ability' for a in self.run_cpu(world)['orders'][0]['actions']))
        for e in world['entities']:
            if e['team_id']==0:e['hp']=8
        response=self.run_cpu(world)
        self.assertEqual(len([a for a in response['orders'][0]['actions'] if a['action_type']=='ability']),1)
        repeated=self.engine.simulate(world,response['orders'],1,12345,self.rules,(False,False))
        self.assertEqual(response['result'],repeated['result'])
        # Supplying an explicit recorded CPU order must never run selection again.
        supplied=deepcopy(response['orders']);supplied[0]['actions']=[]
        replay=self.run_cpu(world,orders=supplied)
        self.assertEqual(replay['orders'][0],supplied[0])

    def test_difficulty_and_legacy_rule_behavior(self):
        for level,expected in (("beginner",False),("normal",True),("expert",True)):
            rules=deepcopy(self.rules);rules["simulation"]["ai"]={"default_level":level}
            response=self.run_cpu(self.world(),rules=rules)
            with self.subTest(level=level):
                self.assertEqual(any(a["action_type"]=="ability" for a in response["orders"][0]["actions"]),expected)
        legacy=json.loads((ROOT/"tests/fixtures/interactions/reception-record.json").read_text())
        response=self.engine.simulate(legacy["initial"],[None,None],1,12345,legacy["rules"],(True,False))
        self.assertFalse(any(a["action_type"]=="ability" for a in response["orders"][0]["actions"]))
