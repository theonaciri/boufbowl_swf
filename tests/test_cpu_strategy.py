from copy import deepcopy
import json
import unittest

from backend.engine import Engine
from tools.game_config import ROOT, load_config


class CPUStrategyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Engine()
        cls.rules = load_config()['rules']
        cls.world = json.loads((ROOT/'tests/fixtures/movement_engine_turn.json').read_text())['initial']

    @classmethod
    def tearDownClass(cls):
        cls.engine.close()

    def test_legal_movement_and_pursuit_on_both_sides_and_halftime(self):
        for team in (0, 1):
            for swapped in (False, True):
                for held in (False, True):
                    world = deepcopy(self.world)
                    world['sides_swapped'] = swapped
                    # Distant opponents isolate overextension from combat falls.
                    for e in world['entities']:
                        e['ability_uses_remaining'] = 0
                        e['position']['q'] = -10 if e['team_id'] == 0 else 10
                    if held:
                        carrier = next(e for e in world['entities'] if e['team_id'] != team)
                        world['ball'].update(holder_entity_id=carrier['id'], position=carrier['position'])
                        carrier['status']['carrying_ball'] = True
                    response = self.engine.simulate(world, [None, None], 1, 12345, self.rules,
                                                    (team == 0, team == 1))
                    with self.subTest(team=team, swapped=swapped, held=held):
                        movements = [a for a in response['orders'][team]['actions'] if a['action_type'] == 'move']
                        self.assertTrue(movements)
                        for action in movements:
                            origin = next(e['position'] for e in world['entities'] if e['id'] == action['entity_id'])
                            target = action['params']['target_position']
                            dq, dr = target['q']-origin['q'], target['r']-origin['r']
                            ranges = self.rules['client_ranges']
                            elements = action['params']['elements']
                            safe = sum(elements[e]*ranges[k] for e, k in (
                                ('TERRE', 'earth_distance_bonus'), ('FEU', 'fire_distance_bonus'),
                                ('AIR', 'air_distance_bonus'), ('EAU', 'water_distance_bonus')))
                            self.assertLessEqual(max(abs(dq), abs(dr), abs(dq+dr)),
                                                 safe * ranges['max_distance_factor'])
                            self.assertEqual(sum(elements.values()), 3)
                        tests = [e['params'] for e in response['result']['events'] if e['type'] == 'movement_test']
                        self.assertTrue(tests)
                        self.assertTrue(all(0 <= t['probability'] <= self.rules['simulation']['movement']['overextension']['fall_probability_at_max'] for t in tests))
                        self.assertEqual(response['warnings'], [])

    def tactical_world(self, allies, enemies=(), holder=11):
        world = deepcopy(self.world)
        world['entities'] = []
        for team, positions in enumerate((allies, enemies)):
            for index, spec in enumerate(positions):
                q, r, *stats = spec
                actor = deepcopy(self.world['entities'][team * 5 + index])
                actor.update(position={'q':q,'r':r}, ability_uses_remaining=0)
                if stats:
                    actor['stats'].update(stats[0])
                actor['status'] = dict(stunned=False, knocked_down=False, carrying_ball=actor['id']==holder)
                world['entities'].append(actor)
        world['ball'].update(holder_entity_id=holder, position=next(
            (e['position'] for e in world['entities'] if e['id']==holder), {'q':0,'r':0}))
        return world

    def cpu(self, world, seed=12345, opponent=None, rules=None):
        return self.engine.simulate(world, [None, opponent], 1, seed, rules or self.rules, (True, False))

    def test_risky_scoring_run_is_allowed_but_ordinary_carry_prefers_safe_range(self):
        safe = self.cpu(self.tactical_world([(0,0)]))
        self.assertGreater(safe['orders'][0]['cpu_plan']['roles'][0]['movement_risk'], 0)
        scoring = self.tactical_world([(5,0)])
        success, failure = self.cpu(scoring), self.cpu(scoring, seed=4)
        self.assertGreater(success['orders'][0]['cpu_plan']['roles'][0]['movement_risk'], safe['orders'][0]['cpu_plan']['roles'][0]['movement_risk'])
        self.assertEqual(success['orders'], failure['orders'])
        self.assertIn('goal', [e['type'] for e in success['result']['events']])
        self.assertIn('fall', [e['type'] for e in failure['result']['events']])

    def test_runs_then_passes_to_parallel_teammate_who_catches_and_scores(self):
        world = self.tactical_world([(3,0,{'precision':25}), (6,3,{'precision':25})])
        response = self.cpu(world)
        actions = response['orders'][0]['actions']
        self.assertTrue(all(any(a['entity_id']==identity and a['action_type']=='move' for a in actions) for identity in (11,12)))
        thrown = next(e for e in response['result']['events'] if e['type']=='throw')
        caught = next(e for e in response['result']['events'] if e['type']=='catch')
        self.assertGreater(thrown['tick'], 1)
        self.assertNotEqual(thrown['params']['start_position'], world['entities'][0]['position'])
        self.assertEqual(caught['actor'], 12)
        self.assertIn('goal', [e['type'] for e in response['result']['events']])

    def test_switches_across_pitch_to_a_free_teammate(self):
        # Strong blockers with moderate Fire leave a viable aerial lane.
        # Fire is now the interception characteristic, separate from Air.
        enemy_stats = {'strength':22, 'agility':10}
        world = self.tactical_world([(-5,9,{'precision':25,'strength':3,'agility':3}),
                                     (3,-3,{'precision':25,'endurance':5})],
                                    [(-3,9,enemy_stats),(-2,8,enemy_stats),(-4,10,enemy_stats),
                                     (-1,7,enemy_stats),(0,9,enemy_stats)])
        response = self.cpu(world)
        thrown = next(e for e in response['result']['events'] if e['type']=='throw')
        self.assertGreaterEqual(thrown['params']['start_position']['r'] - thrown['params']['target_position']['r'], 3)
        self.assertEqual(thrown['params']['target_entity_id'], 12)
        self.assertTrue(any(e['type']=='catch' and e['actor']==12 for e in response['result']['events']))

    def test_high_fire_defenders_change_pass_plan_without_reading_orders(self):
        strategies = []
        for fire in (10, 22):
            enemies = [(q,r,{'strength':22,'agility':fire,'precision':10}) for q,r in
                       [(-3,9),(-2,8),(-4,10),(-1,7),(0,9)]]
            world = self.tactical_world([(-5,9,{'precision':25,'strength':3,'agility':3}),
                                         (3,-3,{'precision':25,'endurance':5})], enemies)
            strategies.append(self.cpu(world)['orders'][0]['cpu_plan']['strategy'])
        self.assertEqual(strategies, ['pass', 'carry'])

    def test_carrier_retreats_or_forces_contact_according_to_stats(self):
        enemy_stats = {'strength':22, 'agility':22}
        opponents = [(-2,9,enemy_stats),(-2,8,enemy_stats),(-3,10,enemy_stats),
                     (-1,7,enemy_stats),(0,9,enemy_stats)]
        for stats, strategy, event in [({'strength':2,'agility':1}, 'retreat', None),
                                       ({'strength':25,'agility':1}, 'carry', 'duel'),
                                       ({'strength':2,'agility':30}, 'carry', 'dodge')]:
            with self.subTest(stats=stats):
                result = self.cpu(self.tactical_world([(-4,9,stats)], opponents))
                self.assertEqual(result['orders'][0]['cpu_plan']['strategy'], strategy)
                self.assertEqual(result['result']['final_ball_state']['holder_entity_id'], 11)
                if event:
                    self.assertIn(event, [e['type'] for e in result['result']['events']])
                else:
                    self.assertNotIn('duel', [e['type'] for e in result['result']['events']])

    def test_receiver_selection_changes_when_precision_changes(self):
        for precision, expected in [((5,25),13), ((25,5),12)]:
            world = self.tactical_world([(0,0,{'precision':25}), (3,3,{'precision':precision[0]}),
                                         (6,-3,{'precision':precision[1]})])
            response = self.cpu(world)
            self.assertEqual(response['orders'][0]['cpu_plan']['pass']['receiver'], expected)
            self.assertTrue(any(e['type']=='catch' and e['actor']==expected for e in response['result']['events']))

    def test_faster_retriever_is_preferred_at_similar_distance(self):
        for endurance, expected in [((2,20),12), ((20,2),11)]:
            world = self.tactical_world([(-6,0,{'endurance':endurance[0]}),
                                         (-6,1,{'endurance':endurance[1]})], holder=None)
            response = self.cpu(world)
            retriever = next(r for r in response['orders'][0]['cpu_plan']['roles'] if r['role']=='retriever')
            self.assertEqual(retriever['entity_id'], expected)
            self.assertTrue(any(e['type']=='pickup' and e['actor']==expected for e in response['result']['events']))

    def test_injured_carrier_avoids_a_damaging_exchange(self):
        world = self.tactical_world([(0,0,{'strength':11})],
                                    [(2,0,{'strength':12}),(1,2,{'strength':12}),(3,-2,{'strength':12})])
        healthy = self.cpu(world)
        world['entities'][0]['hp'] = 1
        injured = self.cpu(world)
        self.assertGreater(healthy['orders'][0]['actions'][0]['params']['elements']['TERRE'], 0)
        self.assertGreater(injured['orders'][0]['actions'][0]['params']['elements']['FEU'], 0)
        self.assertEqual(injured['result']['final_entity_states'][0]['hp'], 1)

    def test_moving_passes_work_on_opposite_side_and_after_halftime(self):
        for team in (0, 1):
            for swapped in (False, True):
                world = self.tactical_world([(3,0,{'precision':25}), (6,3,{'precision':25})])
                world['sides_swapped'] = swapped
                right = (team == 0) != swapped
                for actor in world['entities']:
                    actor['team_id'] = team
                    if not right:
                        actor['position']['q'] = -actor['position']['q']-actor['position']['r']
                response = self.engine.simulate(world, [None, None], 1, 12345, self.rules, (team==0, team==1))
                with self.subTest(team=team, swapped=swapped):
                    self.assertEqual(response['warnings'], [])
                    self.assertTrue(any(e['type']=='throw' for e in response['result']['events']))
                    self.assertTrue(any(e['type']=='goal' and e['params']['team']==team for e in response['result']['events']))

    def test_anticipates_a_pass_and_uses_fire_to_intercept(self):
        world = self.tactical_world([(-1,1),(1,2,{'precision':25}),(-4,-3),(-7,0),(-5,4)],
                                    [(3,0),(0,5,{'precision':20}),(-3,-5),(8,6),(10,-6)], holder=21)
        rules = deepcopy(self.rules)
        rules['simulation']['combat']['trigger_distance_cells'] = .01
        # Keep an early interception window with the faster v2 Air flight.
        rules['simulation']['ball']['intercept_height_threshold'] = 2
        opponent = {'player_id':'human','team_index':1,'turn_number':1,'nonce':'pass','actions':[
            {'entity_id':21,'action_type':'throw','params':{'target_entity_id':22,'elements':dict(TERRE=0,FEU=0,AIR=3,EAU=0)}},
            {'entity_id':22,'action_type':'wait','params':{'elements':dict(TERRE=0,FEU=0,AIR=3,EAU=0)}}]}
        response = self.cpu(world, opponent=opponent, rules=rules)
        self.assertTrue(any(e['type']=='catch' and e['actor']==12 and e['params']['interception']
                            for e in response['result']['events']))
        no_pass = deepcopy(opponent)
        no_pass['actions'][0]['action_type'] = 'wait'
        # CPU choices may depend on visible stats/positions, never the submitted
        # human order or RNG seed. The interception is a prediction, not a cheat.
        other = self.cpu(world, opponent=no_pass, seed=999, rules=rules)
        self.assertEqual(response['orders'][0], other['orders'][0])

    def test_support_has_width_cover_and_a_strong_screen(self):
        world = self.tactical_world([(0,0,{'precision':25}), (3,3,{'precision':25}),
                                     (-3,-4,{'strength':25}),(-5,5,{'strength':5}),(-7,0,{'strength':5})])
        response = self.cpu(world)
        roles = {r['role']:r['entity_id'] for r in response['orders'][0]['cpu_plan']['roles']}
        self.assertEqual(roles['screen'], 13)
        self.assertIn('parallel_support', roles)
        self.assertIn('cover', roles)
        movements = [a['params']['target_position'] for a in response['orders'][0]['actions'] if a['action_type']=='move']
        self.assertEqual(len(movements), len({(p['q'],p['r']) for p in movements}))
        self.assertGreater(max(p['r'] for p in movements)-min(p['r'] for p in movements), 3)

    def test_recorded_cpu_reception_allocation_is_immutable(self):
        record = json.loads((ROOT/'tests/fixtures/interactions/reception-record.json').read_text())
        supplied = deepcopy(record['orders'])
        receiver = next(a for a in supplied[0]['actions'] if a['entity_id'] == 12)
        receiver['params']['elements'] = dict(TERRE=0, FEU=3, AIR=0, EAU=0)
        before = deepcopy(supplied)
        response = self.engine.simulate(record['initial'], supplied, 1, 12345, self.rules, (True, False))
        self.assertEqual(response['orders'], before)
