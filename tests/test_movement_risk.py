from copy import deepcopy
import json
import unittest
from backend.engine import Engine
from backend.turn_adapter import adapt_turn
from tools.flash_protocol import Codec
from tools.game_config import ROOT,load_config


class MovementRiskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine=Engine();cls.rules=load_config()['rules']
        cls.base=json.loads((ROOT/'tests/fixtures/movement_engine_turn.json').read_text())['initial']

    @classmethod
    def tearDownClass(cls):cls.engine.close()

    def simulate(self,distance,elements=None,probability=.6,seed=1,carrier=False):
        world=deepcopy(self.base);world['entities']=[world['entities'][0]]
        actor=world['entities'][0];actor.update(position={'q':0,'r':0},hp=16,max_hp=16)
        actor['status']=dict(stunned=False,knocked_down=False,carrying_ball=carrier)
        world['ball'].update(holder_entity_id=actor['id'] if carrier else None,position={'q':0,'r':0},in_flight=False)
        rules=deepcopy(self.rules);rules['simulation']['movement']['overextension']['fall_probability_at_max']=probability
        actions=[{'entity_id':actor['id'],'action_type':'move','params':{'target_position':{'q':distance,'r':0},'elements':elements or {'TERRE':3,'FEU':0,'AIR':0,'EAU':0}}}]
        orders=[{'player_id':str(t),'team_index':t,'turn_number':1,'nonce':'risk','actions':actions if t==0 else []} for t in (0,1)]
        response=self.engine.simulate(world,orders,1,seed,rules,(False,False))
        return dict(initial=world,rules=rules,orders=response['orders'],result=response['result'])

    def test_safe_range_uses_no_random_roll_and_orange_range_can_fall(self):
        safe=self.simulate(6);risky=self.simulate(7)
        self.assertFalse(any(e['type']=='fall' for e in safe['result']['events']))
        test=next(e['params'] for e in safe['result']['events'] if e['type']=='movement_test')
        self.assertEqual(test['safe_range'],6);self.assertIsNone(test['random_draw'])
        fall=next(e for e in risky['result']['events'] if e['type']=='fall')
        self.assertGreater(fall['params']['probability'],0)
        self.assertTrue(risky['result']['final_entity_states'][0]['status']['knocked_down'])
        scenario=adapt_turn(risky)
        self.assertFalse(scenario['boufbowlerTracks'][0]['movementTest']['success'])
        self.assertIn(10,[e['interactionDetails']['type'] for e in scenario['interaction']])
        Codec().encode('ResolutionScenarioMessage',scenario)

    def test_probability_grows_toward_outer_range_once_per_runner(self):
        def test(distance):
            record=self.simulate(distance,{'TERRE':0,'FEU':0,'AIR':0,'EAU':3},probability=.01,seed=999999)
            return next(e['params'] for e in record['result']['events'] if e['type']=='movement_test')
        inner,outer=test(10),test(11)
        self.assertLess(inner['probability'],outer['probability'])
        self.assertEqual(inner['random_draw'],outer['random_draw'])
        self.assertEqual(outer['safe_range'],9);self.assertAlmostEqual(outer['max_range'],11.97)

    def test_outside_max_is_rejected_and_failed_carrier_drops_ball(self):
        outside=self.simulate(8)
        self.assertEqual(outside['result']['final_entity_states'][0]['position'],{'q':0,'r':0})
        fallen=self.simulate(7,carrier=True)
        self.assertIsNone(fallen['result']['final_ball_state']['holder_entity_id'])
        self.assertTrue(any(e['type']=='ball_drop' for e in fallen['result']['events']))
        scenario=adapt_turn(fallen)
        fall=next(e for e in scenario['interaction'] if e['interactionDetails']['type']==10)
        self.assertIn('ballDispersion',fall['interactionDetails']['fallDetails'])

    def test_disable_probability_keeps_range_limits_and_replay_is_deterministic(self):
        record=self.simulate(7,probability=0)
        self.assertFalse(any(e['type']=='fall' for e in record['result']['events']))
        self.assertEqual(record['result']['final_entity_states'][0]['position'],{'q':7,'r':0})
        replay=self.engine.simulate(record['initial'],record['orders'],1,1,record['rules'],(False,False))
        self.assertEqual(replay['result'],record['result'])

    def test_period_announcements_match_the_fourteen_turn_reference(self):
        record=self.simulate(1);record['rules']['match'].update(turns_per_match=14,turns_per_period=7)
        record['presentation']={'interactions':True}
        for turn,status in ((5,1),(7,2),(12,3)):
            record['result']['turn_number']=turn
            banner=adapt_turn(record)['periodInformations']
            self.assertEqual(banner['status'],status)
            self.assertEqual(banner['remainingPeriodTurns'],0 if status==2 else 2)
        record['result']['turn_number']=14
        self.assertNotIn('periodInformations',adapt_turn(record))

    def test_observed_class_health_and_regeneration_intervals(self):
        c=load_config()['rules']['classes']['overrides']
        for name,health,interval in [('ROUBLARD',10,3),('SACRIEUR',16,4),('SRAM',11,3),('SADIDA',13,2)]:
            with self.subTest(name=name):
                self.assertEqual(c[name]['health'],health)
                self.assertEqual(c[name]['regeneration'],interval)
