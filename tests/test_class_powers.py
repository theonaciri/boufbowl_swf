from copy import deepcopy
import json
import unittest
from backend.engine import Engine
from backend.service import Service
from backend.storage import ServiceError
from backend.turn_adapter import adapt_turn
from tools.flash_protocol import Codec
from tools.game_config import ROOT, load_config, resolve_stadium
from tools.power_descriptions import client_abilities


class ClassPowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Engine()
        cls.rules = load_config()['rules']
        cls.base = json.loads((ROOT/'tests/fixtures/movement_engine_turn.json').read_text())['initial']

    @classmethod
    def tearDownClass(cls):
        cls.engine.close()

    def world(self, name='Cra'):
        world=deepcopy(self.base)
        template=world['entities'][0]
        world['entities']=[]
        for identity,team,position in [(1,0,(-8,-3)),(2,0,(-8,3)),(3,1,(8,-3)),(4,1,(8,3))]:
            e=deepcopy(template)
            e.update(id=identity,team_id=team,position=dict(zip(('q','r'),position)),hp=8,max_hp=16,
                     ability_uses_remaining=2,class_name=name if identity==1 else 'Iop')
            e['status']=dict(stunned=False,knocked_down=False,carrying_ball=False)
            e.pop('precise_position',None)
            world['entities'].append(e)
        world['ball'].update(position={'q':0,'r':0},holder_entity_id=None,in_flight=False)
        return world

    def run_power(self, world, actions=None, other=None, seed=12345, rules=None):
        orders=[{'player_id':str(t),'team_index':t,'turn_number':1,'nonce':'power-test','actions':a}
                for t,a in enumerate([actions or [{'entity_id':1,'action_type':'ability','params':{}}],other or []])]
        response=self.engine.simulate(world,orders,1,seed,rules or self.rules,(False,False))
        return response

    def test_all_requested_effects_and_expiry(self):
        expected={'Sadida':('enemies',{'range':-1}), 'Enutrof':('allies',{'elements':{'EAU':3}}),
                  'Iop':('allies',{'elements':{'TERRE':3}}), 'Osamodas':('allies',{'elements':dict.fromkeys(('TERRE','FEU','AIR','EAU'),1)}),
                  'Cra':('allies',{'range':1}), 'Sacrier':('allies',{'hp':-1,'elements':dict.fromkeys(('TERRE','FEU','AIR','EAU'),2)}),
                  'Rogue':('enemies',{'hp':-2}), 'Eniripsa':('allies',{'hp':2}), 'Xelor':('allies',{'elements':{'AIR':3}}),
                  'Sram':('allies',{'elements':{'FEU':3}}), 'Feca':('enemies',{'attack':-1}), 'Pandawa':('allies',{'attack':1})}
        for name,(target,effects) in expected.items():
            with self.subTest(name=name):
                world=self.world(name);result=self.run_power(world)['result']
                event=next(e for e in result['events'] if e['type']=='ability')['params']
                self.assertEqual(event['targets'],[1,2] if target=='allies' else [3,4])
                for key,value in effects.items():
                    if key!='hp':self.assertEqual(event[key],value)
                for before,after in zip(world['entities'],result['final_world_state']['entities']):
                    self.assertEqual(before['stats'],after['stats'])
                    self.assertEqual(sum(after['elements'].values()),0)
                    self.assertFalse(set(after)&{'range_bonus','attack_bonus','power_locked'})
                    self.assertEqual(after['hp'],8+(effects.get('hp',0) if before['id'] in event['targets'] else 0))
                self.assertEqual(result['final_entity_states'][0]['ability_uses_remaining'],1)
                record=dict(initial=world,orders=self.run_power(world)['orders'],result=result)
                scenario=adapt_turn(record)
                Codec().encode('ResolutionScenarioMessage',scenario)
                for item in scenario['classOrder'][0]['target']:
                    self.assertEqual(item.get('preResolutionHitPointsDelta',0),effects.get('hp',0))
                    expected_numbers=[v for v in [effects.get('hp',0),*effects.get('elements',{}).values(),effects.get('range',0),effects.get('attack',0)] if v]
                    self.assertEqual(item['effectDeltas'],list(dict.fromkeys(expected_numbers)))

    def test_ecaflip_both_outcomes_and_reproducibility(self):
        # Recorded experimental rules retain the former random stat ability.
        rules = deepcopy(self.rules)
        rules['abilities']['Ecaflip'] = {'name':'Ecaflip', 'verified':False, 'target':'allies',
            'elements':dict.fromkeys(('TERRE','FEU','AIR','EAU'),2), 'enemy_chance':.5,
            'enemy_elements':dict.fromkeys(('TERRE','FEU','AIR','EAU'),1)}
        world=self.world('Ecaflip');outcomes=set()
        for seed in range(1,100):
            response=self.run_power(world,seed=seed,rules=rules);result=response['result']
            event=result['events'][0]['params'];outcomes.add(event['target'])
            self.assertEqual(event['elements'],dict.fromkeys(('TERRE','FEU','AIR','EAU'),1 if event['target']=='enemies' else 2))
            self.assertEqual(rules['abilities']['Ecaflip']['enemy_chance'],.5)
            repeated=self.engine.simulate(world,response['orders'],1,seed,rules,(False,False))['result']
            self.assertEqual(result,repeated)
        self.assertEqual(outcomes,{'allies','enemies'})

    def test_range_extends_movement_and_then_expires(self):
        world=self.world();world['entities'][1]['position']={'q':-8,'r':0}
        actions=[{'entity_id':1,'action_type':'ability','params':{}},
                 {'entity_id':2,'action_type':'move','params':{'target_position':{'q':0,'r':0},'elements':{'TERRE':3,'FEU':0,'AIR':0,'EAU':0}}}]
        after=self.run_power(world,actions)['result']['final_world_state']
        self.assertEqual(after['entities'][1]['position'],{'q':0,'r':0})
        self.assertEqual(after['entities'][0]['position'],world['entities'][0]['position'])
        rules=deepcopy(self.rules);rules['abilities']['Cra']['range']=0
        ordinary=self.run_power(world,actions,rules=rules)['result']['final_world_state']
        self.assertEqual(ordinary['entities'][1]['position'],{'q':-8,'r':0})

    def test_element_bonuses_change_characteristics_not_slots(self):
        world=self.world('Iop');world['entities'][1]['position']={'q':0,'r':0};world['entities'][2]['position']={'q':1,'r':0}
        result=self.run_power(world)['result']
        duel=next(e for e in result['events'] if e['type']=='duel')
        self.assertEqual(duel['actor'],2)
        self.assertEqual(result['final_entity_states'][1]['hp'],8)
        self.assertLess(result['final_entity_states'][2]['hp'],8)
        response=self.run_power(world)
        scenario=adapt_turn(dict(initial=world,orders=response['orders'],result=response['result'],rules=self.rules))
        fight=next(i for i in scenario['interaction'] if i['interactionDetails']['type']==20)
        self.assertEqual(fight['interactionDetails']['fightTest']['score'][0]['inherentScore'],world['entities'][1]['stats']['strength']+3)

    def test_caster_cannot_move_or_pick_up_even_when_buffed(self):
        world=self.world('Osamodas');world['ball']['position']=deepcopy(world['entities'][0]['position'])
        rules=deepcopy(self.rules);rules['simulation']['actions']['element_effects']['feu']['used_for_pickup']=False
        result=self.run_power(world,rules=rules)['result']
        self.assertFalse(any(e['type'] in ('pickup','catch','throw','move') and e.get('actor')==1 for e in result['events']))
        for extra in ('move','wait','throw','pickup'):
            with self.subTest(extra=extra),self.assertRaises(ServiceError):
                self.run_power(world,[{'entity_id':1,'action_type':'ability','params':{}},{'entity_id':1,'action_type':extra,'params':{}}])
        with self.assertRaises(ServiceError):
            self.run_power(world,[{'entity_id':i,'action_type':'ability','params':{}} for i in (1,2)])

    def test_uses_status_and_mask_validation(self):
        for update in ({'ability_uses_remaining':0},{'hp':0}):
            world=self.world();world['entities'][0].update(update)
            with self.assertRaises(ServiceError):self.run_power(world)
        world=self.world();world['entities'][0]['status']['stunned']=True
        with self.assertRaises(ServiceError):self.run_power(world)
        world=self.world('Zobal');world['entities'][0]['zobal_mask']=1
        for mask in (None,0,1,4):
            with self.subTest(mask=mask),self.assertRaises(ServiceError):self.run_power(world,[{'entity_id':1,'action_type':'ability','params':{'zobal_mask':mask}}])
        response=self.run_power(world,[{'entity_id':1,'action_type':'ability','params':{'zobal_mask':2}}])
        self.assertEqual(response['result']['final_world_state']['entities'][0]['zobal_mask'],2)
        scenario=adapt_turn(dict(initial=world,orders=response['orders'],result=response['result']))
        self.assertEqual(scenario['classOrder'][0]['zobalMask'],2)
        self.assertEqual(scenario['boufbowlerTracks'][0]['order']['zobalMask'],2)
        Codec().encode('ResolutionScenarioMessage',scenario)

    def test_lethal_power_drops_ball_and_opposing_caster_still_casts(self):
        world=self.world('Rogue');world['entities'][2].update(hp=1,class_name='Eniripsa')
        world['ball'].update(holder_entity_id=3,position=deepcopy(world['entities'][2]['position']))
        world['entities'][2]['status']['carrying_ball']=True
        response=self.run_power(world,other=[{'entity_id':3,'action_type':'ability','params':{}}])
        self.assertEqual(len([e for e in response['result']['events'] if e['type']=='ability']),2)
        # A surviving heal at the same power phase can save the carrier.
        self.assertEqual(response['result']['final_world_state']['entities'][2]['hp'],2)
        world['entities'][2]['class_name']='Iop'
        result=self.run_power(world)['result']
        self.assertEqual(result['final_entity_states'][2]['hp'],0)
        self.assertIsNone(result['final_ball_state']['holder_entity_id'])
        self.assertTrue(any(e['type']=='ball_drop' and e['actor']==3 for e in result['events']))

    def test_legacy_recorded_turns_still_reproduce(self):
        for path in (ROOT/'tests/fixtures/interactions').glob('*-record.json'):
            with self.subTest(record=path.name):
                record=json.loads(path.read_text());expected=record['result']
                reproduced=self.engine.simulate(record['initial'],record['orders'],expected['turn_number'],expected['seed'],record['rules'],(False,False))['result']
                self.assertEqual(reproduced['events'],expected['events'])
                self.assertEqual(reproduced['final_state_hash'],expected['final_state_hash'])
                # Events and state remain reproducible with their saved line;
                # the current worker explicitly identifies its corrected goal checks.
                self.assertEqual(reproduced['simulation_version'],expected['simulation_version']+'+goal-zones-1')

    def test_distinct_balanced_base_stats_and_localized_descriptions(self):
        classes=load_config()['rules']['classes'];profiles=[]
        for values in classes['overrides'].values():
            profile=tuple(values[k] for k in ('earth','air','fire','water'))
            self.assertEqual(sum(profile),42);profiles.append(profile)
        self.assertEqual(len(set(profiles)),14)
        for rule in client_abilities(self.rules).values():
            self.assertEqual(set(rule['descriptions']),{'fr','en','de','es'})
            self.assertTrue(all(rule['descriptions'].values()))
        self.assertEqual(resolve_stadium(load_config(),'KARA')['match']['class_ability_uses'],2)


    def test_descriptions_end_with_effects_in_every_language(self):
        from tools.power_descriptions import client_abilities
        for ability in client_abilities(self.rules).values():
            for language,text in ability['descriptions'].items():
                for suffix in ('Un seul pouvoir','One power per team','Eine Kraft pro Team','Un poder por equipo'):
                    self.assertNotIn(suffix,text)
                self.assertTrue(text.endswith('.'),(language,text))

    def test_display_numbers_are_applied_changes_and_never_change_hp(self):
        world=self.world('Enutrof');response=self.run_power(world)
        scenario=adapt_turn(dict(initial=world,orders=response['orders'],result=response['result'],rules=self.rules))
        for target in scenario['classOrder'][0]['target']:
            self.assertNotIn('preResolutionHitPointsDelta',target)
            self.assertEqual(target['effectDeltas'],[3])
        self.assertEqual([e['hp'] for e in response['result']['final_world_state']['entities']],[e['hp'] for e in world['entities']])
        # A heal at the cap is not a fake +2 (and not a +0 popup).
        world=self.world('Eniripsa')
        for entity in world['entities']:entity['hp']=entity['max_hp']
        response=self.run_power(world)
        scenario=adapt_turn(dict(initial=world,orders=response['orders'],result=response['result'],rules=self.rules))
        self.assertTrue(all('preResolutionHitPointsDelta' not in t and 'effectDeltas' not in t for t in scenario['classOrder'][0]['target']))
