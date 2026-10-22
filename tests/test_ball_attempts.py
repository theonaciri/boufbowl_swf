from copy import deepcopy
import json
import unittest

from backend.engine import Engine
from backend.turn_adapter import adapt_turn
from tools.game_config import ROOT, load_config
from tools.flash_protocol import Codec


class BallAttemptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Engine()
        cls.rules = load_config()['rules']
        cls.baseline = json.loads((ROOT/'tests/fixtures/movement_engine_turn.json').read_text())['initial']

    @classmethod
    def tearDownClass(cls):
        cls.engine.close()

    def world(self, passing=False, interceptor=False, friendly=False):
        world = deepcopy(self.baseline)
        left = [e for e in world['entities'] if e['team_id'] == 0]
        right = [e for e in world['entities'] if e['team_id'] == 1]
        world['entities'] = left[:2] if passing else left[:1]
        if interceptor:
            extra = left[2] if friendly else right[0]
            world['entities'].append(extra)
            extra['position'] = {'q':1,'r':0}
        for e in world['entities']:
            e.pop('precise_position', None)
            e['stats']['precision'] = 10
            e['status'].update(stunned=False, knocked_down=False, carrying_ball=False)
        left[0]['position'] = {'q':0,'r':0}
        if passing:
            left[1]['position'] = {'q':6,'r':0}
            left[0]['status']['carrying_ball'] = True
        world['ball'] = {'position':{'q':0,'r':0},'holder_entity_id':left[0]['id'] if passing else None,'in_flight':False}
        return world

    def run_turn(self, world, allocations, rules=None, seed=12345, passing=False):
        actions = {0:[],1:[]}
        for e, (air,fire) in zip(world['entities'],allocations):
            elements = {'TERRE':0,'AIR':air,'FEU':fire,'EAU':3-air-fire}
            actions[e['team_id']].append({'entity_id':e['id'],'action_type':'wait','params':{'elements':elements}})
        if passing:
            actions[0].append({'entity_id':world['entities'][0]['id'],'action_type':'throw',
                               'params':{'elements':actions[0][0]['params']['elements'], 'target_entity_id':world['entities'][1]['id']}})
        orders = [{'player_id':str(t),'turn_number':1,'team_index':t,'nonce':'ball-test','actions':actions[t]} for t in (0,1)]
        rules = deepcopy(rules or self.rules)
        rules['simulation']['combat']['trigger_distance_cells'] = .01
        response = self.engine.simulate(world,orders,1,seed,rules,(False,False))
        return {'initial':world,'orders':response['orders'],'result':response['result'],'rules':rules}

    def fixed_chance(self, chance):
        rules = deepcopy(self.rules)
        rules['simulation']['simulation'].update(probability_min=chance, probability_max=chance)
        return rules

    def successful_throw_failed_catches(self):
        rules = deepcopy(self.rules)
        rules['simulation']['simulation'].update(probability_min=0,probability_max=1,
            throw_base=1,throw_stat=0,distance_penalty=0,catch_base=0,catch_stat=0,catch_air=0,catch_feu=0)
        rules['simulation']['probabilities']['air_precision_per_action'] = 0
        rules['simulation']['ball']['intercept_height_threshold'] = 10
        return rules

    def test_ground_pickups_fail_and_exhaust_exact_action_budget(self):
        for air,fire in ((0,0),(1,0),(0,1),(2,0),(0,2),(1,1),(1,2),(3,0)):
            with self.subTest(air=air,fire=fire):
                record = self.run_turn(self.world(),[(air,fire)],self.fixed_chance(0))
                failures = [e for e in record['result']['events'] if e['type']=='pickup_fail']
                self.assertEqual(len(failures),air+fire)
                self.assertEqual([e['params']['attempt'] for e in failures],list(range(1,air+fire+1)))
                self.assertEqual(len({e['tick'] for e in failures}),len(failures))
                self.assertIsNone(record['result']['final_world_state']['ball']['holder_entity_id'])

    def test_ground_pickup_stops_after_success(self):
        record = self.run_turn(self.world(),[(1,2)],self.fixed_chance(1))
        attempts = [e for e in record['result']['events'] if e['type'] in ('pickup','pickup_fail')]
        self.assertEqual(len(attempts),1)
        self.assertEqual(attempts[0]['type'],'pickup')

    def test_attempt_budgets_reset_between_turns(self):
        rules = self.fixed_chance(0)
        first = self.run_turn(self.world(),[(2,1)],rules)
        second = self.run_turn(first['result']['final_world_state'],[(2,1)],rules)
        self.assertEqual(sum(e['type']=='pickup_fail' for e in second['result']['events']),3)

    def test_intended_receiver_requires_air_and_cannot_use_fire_in_flight(self):
        for air,fire in ((0,3),(1,2)):
            with self.subTest(air=air):
                world = self.world(passing=True)
                record = self.run_turn(world,[(3,0),(air,fire)],self.fixed_chance(1),passing=True)
                catches = [e for e in record['result']['events'] if e['type']=='catch']
                self.assertEqual(bool(catches),bool(air))
                if catches:
                    self.assertFalse(catches[0]['params']['interception'])
                    self.assertEqual(catches[0]['params']['action'],'air')

    def test_only_opponents_with_fire_attempt_to_intercept(self):
        for friendly in (False,True):
            for air,fire in ((3,0),(0,3)):
                with self.subTest(friendly=friendly,fire=fire):
                    world = self.world(passing=True,interceptor=True,friendly=friendly)
                    record = self.run_turn(world,[(3,0),(3,0),(air,fire)],self.fixed_chance(1),passing=True)
                    catches = [e for e in record['result']['events'] if e['type']=='catch']
                    intercepted = bool(fire) and not friendly
                    self.assertEqual(catches[0]['actor'],world['entities'][2 if intercepted else 1]['id'])
                    self.assertEqual(catches[0]['params']['interception'],intercepted)
                    if friendly:
                        attempts = [e for e in record['result']['events']
                                    if e['type'] in ('catch','catch_fail') and e['actor']==world['entities'][2]['id']]
                        self.assertEqual(attempts,[])

    def test_intended_retries_use_air_and_ground_retries_use_remaining_fire(self):
        for air,fire in ((3,0),(1,2)):
            world = self.world(passing=True)
            receiver = world['entities'][1]['id']
            record = self.run_turn(world,[(3,0),(air,fire)],self.successful_throw_failed_catches(),passing=True)
            catches = [e for e in record['result']['events'] if e['type']=='catch_fail' and e['actor']==receiver]
            pickups = [e for e in record['result']['events'] if e['type']=='pickup_fail' and e['actor']==receiver]
            self.assertEqual(len(catches),air)
            self.assertEqual(len(pickups),fire)
            self.assertEqual(len({e['tick'] for e in catches+pickups}),air+fire)

    def test_air_adds_ten_points_and_fire_does_not_boost_intended_reception(self):
        world = self.world(passing=True)
        record = self.run_turn(world,[(3,0),(1,2)],passing=True)
        event = next(e for e in record['result']['events'] if e['type'] in ('catch','catch_fail'))
        self.assertAlmostEqual(event['params']['catch_chance'],.35+.3+.1)

    def test_interception_retries_are_limited_to_fire_actions(self):
        world = self.world(passing=True,interceptor=True)
        record = self.run_turn(world,[(3,0),(0,0),(0,3)],self.successful_throw_failed_catches(),passing=True)
        failures = [e for e in record['result']['events'] if e['type']=='catch_fail' and e['actor']==world['entities'][2]['id']]
        self.assertEqual(len(failures),3)
        self.assertTrue(all(e['params']['interception'] and e['params']['action']=='fire' for e in failures))

    def test_fire_can_intercept_an_inaccurate_pass(self):
        world = self.world(passing=True,interceptor=True)
        rules = self.successful_throw_failed_catches()
        rules['simulation']['simulation'].update(throw_base=0,catch_base=1)
        record = self.run_turn(world,[(3,0),(3,0),(0,3)],rules,passing=True)
        thrown = next(e for e in record['result']['events'] if e['type']=='throw')
        caught = next(e for e in record['result']['events'] if e['type']=='catch')
        self.assertFalse(thrown['params']['success'])
        self.assertEqual(caught['actor'],world['entities'][2]['id'])
        self.assertTrue(caught['params']['interception'])

    def test_failed_pickup_can_succeed_on_a_later_attempt_deterministically(self):
        rules = self.fixed_chance(.5)
        for seed in range(1,101):
            record = self.run_turn(self.world(),[(1,2)],rules,seed=seed)
            attempts = [e for e in record['result']['events'] if e['type'] in ('pickup','pickup_fail')]
            if len(attempts)>1 and attempts[-1]['type']=='pickup':
                repeated = self.run_turn(self.world(),[(1,2)],rules,seed=seed)
                self.assertEqual(record['result'],repeated['result'])
                self.assertTrue(all(e['type']=='pickup_fail' for e in attempts[:-1]))
                return
        self.fail('No fail-then-success pickup found across 100 seeds')

    def test_failed_pickups_render_as_failed_maneuvers(self):
        record = self.run_turn(self.world(),[(1,2)],self.fixed_chance(0))
        scenario = adapt_turn(record)
        pickups = [i['interactionDetails'] for i in scenario['interaction'] if i['interactionDetails']['type']==11]
        self.assertEqual(len(pickups),3)
        self.assertTrue(all(not p['maneuverTest']['success'] for p in pickups))
        codec = Codec()
        decoded = codec.open_envelope(codec.envelope('RESOLUTION_SCENARIO',scenario))['payload']
        self.assertEqual(len(decoded['interaction']),3)

    def test_failed_catch_retries_render_before_the_final_reception(self):
        rules = self.successful_throw_failed_catches()
        rules['simulation']['simulation']['catch_base'] = .5
        for seed in range(1, 101):
            record = self.run_turn(self.world(passing=True), [(3, 0), (3, 0)], rules, seed=seed, passing=True)
            attempts = [e for e in record['result']['events'] if e['type'] in ('catch', 'catch_fail')]
            if len(attempts) < 2 or attempts[0]['type'] != 'catch_fail' or attempts[-1]['type'] != 'catch':
                continue
            scenario = adapt_turn(record)
            receptions = [i for i in scenario['interaction'] if i['interactionDetails']['type'] == 14]
            self.assertEqual([i['interactionDetails']['maneuverTest']['success'] for i in receptions],
                             [e['type'] == 'catch' for e in attempts])
            passed = next(i['interactionDetails'] for i in scenario['interaction'] if i['interactionDetails']['type'] == 21)
            self.assertEqual(passed['passDetails']['nextInteractionId'], receptions[-1]['interactionId'])
            self.assertEqual(record['result']['final_ball_state']['holder_entity_id'], 12)
            Codec().encode('ResolutionScenarioMessage', scenario)
            return
        self.fail('No failed-then-successful catch across 100 seeds')
