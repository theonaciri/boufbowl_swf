from copy import deepcopy
import json
from pathlib import Path
import unittest

from backend.engine import Engine
from backend.placement import placement_zones
from tools.game_config import ROOT, load_config


class GameplayFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Engine()
        cls.rules = load_config()['rules']
        cls.baseline = json.loads((ROOT/'tests/fixtures/movement_engine_turn.json').read_text())['initial']

    @classmethod
    def tearDownClass(cls):
        cls.engine.close()

    def simulate(self, world, actions=None, rules=None, acting_team=0):
        orders = [{'player_id':str(t),'turn_number':1,'team_index':t,'nonce':'probe',
                   'actions':(actions or []) if t == acting_team else []} for t in (0,1)]
        return self.engine.simulate(world, orders, 1, 12345, rules or self.rules, (False,False))['result']

    def test_ball_pickup_covers_all_six_adjacent_cells_but_not_two_cells(self):
        for fire, air in ((1,0),(0,1),(1,1),(0,0)):
            for position in ((0,0),(1,0),(0,1),(-1,1),(-1,0),(0,-1),(1,-1),(2,0),(1,1)):
                with self.subTest(position=position, fire=fire, air=air):
                    world = deepcopy(self.baseline)
                    actor = world["entities"][0]
                    world["entities"] = [actor]
                    actor["position"] = {"q": position[0], "r": position[1]}
                    actor.pop("precise_position", None)
                    actor["status"].update(carrying_ball=False, stunned=False, knocked_down=False)
                    world["ball"] = {"position": {"q":0,"r":0}, "holder_entity_id":None, "in_flight":False}
                    result = self.simulate(world, [{"entity_id":actor["id"], "action_type":"wait", "params":{"elements":{"TERRE":0,"FEU":fire,"AIR":air,"EAU":3-fire-air}}}])
                    pickups = [e for e in result["events"] if e["type"] == "pickup"]
                    self.assertEqual(bool(pickups), bool(fire or air) and max(abs(position[0]),abs(position[1]),abs(sum(position))) <= 1)

    def test_air_enables_reception_and_feu_alone_does_not(self):
        record = json.loads((ROOT/'tests/fixtures/interactions/reception-record.json').read_text())
        # Force probabilities to isolate eligibility from the random catch draw.
        rules = deepcopy(self.rules)
        rules['simulation']['simulation'].update(probability_min=1, probability_max=1)
        for air in (0,1):
            with self.subTest(air=air):
                actions = deepcopy(record['orders'][0]['actions'])
                receiver = next(a for a in actions if a['entity_id']==12)
                receiver['params']['elements'] = {'TERRE':0,'FEU':3-air,'AIR':air,'EAU':0}
                result = self.simulate(deepcopy(record['initial']), actions, rules)
                catches = [e for e in result['events'] if e['type']=='catch' and e['actor']==12]
                self.assertEqual(bool(catches), bool(air))

    def test_air_reception_can_still_fail_probability(self):
        record = json.loads((ROOT/'tests/fixtures/interactions/rebound-record.json').read_text())
        result = self.simulate(record['initial'], record['orders'][0]['actions'], record['rules'])
        self.assertIn('catch_fail', [e['type'] for e in result['events']])
        self.assertNotIn('catch', [e['type'] for e in result['events']])

    def test_goals_use_vertical_line_both_sides_and_halftime(self):
        for team in (0,1):
            for swapped in (False,True):
                for row in (-3,-2,2,3):
                    right = (team == 0) != swapped
                    for past in (False,True):
                        # Logical x is q+r/2; the line itself is not inside the end zone.
                        q = (16 if past else 15) - row//2
                        if not right: q = -q-row
                        with self.subTest(team=team,swapped=swapped,row=row,past=past):
                            world = deepcopy(self.baseline)
                            actor = next(e for e in world['entities'] if e['team_id']==team)
                            actor['position'] = {'q':q,'r':row}
                            world['sides_swapped'] = swapped
                            world['ball'].update(holder_entity_id=actor['id'],position=deepcopy(actor['position']))
                            actor['status']['carrying_ball']=True
                            events = self.simulate(world)['events']
                            goals = [e for e in events if e['type']=='goal']
                            expected = abs(q+row/2) > 15.5
                            self.assertEqual(bool(goals),expected)
                            if goals: self.assertEqual(goals[0]['params']['team'],team)

    def test_end_zones_contain_exactly_two_outer_columns_on_even_and_odd_rows(self):
        self.assertEqual(self.rules['simulation']['ball']['goal_line_half_width'],15.5)
        for row in (-10,-9,0,1,9,10):
            for team in (0,1):
                scoring=[]
                for column in range(12,18):
                    horizontal=column+(row%2)/2
                    if team==1: horizontal=-horizontal
                    world=deepcopy(self.baseline)
                    actor=next(e for e in world['entities'] if e['team_id']==team)
                    actor['position']={'q':int(horizontal-row/2),'r':row}
                    world['ball'].update(holder_entity_id=actor['id'],position=deepcopy(actor['position']))
                    actor['status']['carrying_ball']=True
                    if any(e['type']=='goal' for e in self.simulate(world)['events']): scoring.append(column)
                with self.subTest(row=row,team=team): self.assertEqual(scoring,[16,17])

    def test_running_carrier_crosses_end_zone_boundary_before_goal_animation(self):
        from backend.turn_adapter import adapt_turn
        for row in (0,1,-1):
            for team in (0,1):
                for swapped in (False,True):
                    world=deepcopy(self.baseline)
                    actor=next(e for e in world['entities'] if e['team_id']==team)
                    world['entities']=[actor]
                    world['sides_swapped']=swapped
                    direction=1 if (team==0)!=swapped else -1
                    q=15-row//2
                    if direction<0: q=-q-row
                    actor['position']={'q':q,'r':row}
                    actor['status']['carrying_ball']=True
                    world['ball'].update(holder_entity_id=actor['id'],position=deepcopy(actor['position']))
                    action={'entity_id':actor['id'],'action_type':'move','params':{
                        'target_position':{'q':q+direction,'r':row},'elements':{'TERRE':0,'FEU':0,'AIR':0,'EAU':3}}}
                    result=self.simulate(world,[action],acting_team=team)
                    goal=next(e for e in result['events'] if e['type']=='goal')
                    moves=[e for e in result['events'] if e['type']=='move' and e['actor']==actor['id'] and e['tick']<=goal['tick']]
                    point=moves[-1]['params']['precise_position']
                    with self.subTest(row=row,team=team,swapped=swapped):
                        self.assertGreater(direction*(point['q']+point['r']/2)/point['scale'],15.5)
                        self.assertGreater(direction*(goal['params']['position']['q']+row/2),15.5)
                        orders=[{'actions':[action] if side==team else []} for side in (0,1)]
                        scenario=adapt_turn({'initial':world,'orders':orders,'result':result,'rules':self.rules})
                        touchdown=next(i['interactionDetails'] for i in scenario['interaction'] if i['interactionDetails']['type']==12)
                        track=next(t for t in scenario['boufbowlerTracks'] if t['boufbowlerId']==str(actor['id']))
                        arrival=next(i['movement'] for i in track['item'] if i['type']==1 and i['movement']['positions'][-1]=={
                            'x':goal['params']['position']['q'],'y':row})
                        self.assertLessEqual(arrival['endTick'],touchdown['startTick'])

    def test_crossing_without_ball_or_crossing_own_line_does_not_score(self):
        world = deepcopy(self.baseline)
        actor = world['entities'][0]; actor['position']={'q':13,'r':0}
        self.assertNotIn('goal',[e['type'] for e in self.simulate(world)['events']])
        actor['position']={'q':-13,'r':0}
        world['ball'].update(holder_entity_id=actor['id'],position=deepcopy(actor['position']))
        actor['status']['carrying_ball']=True
        self.assertNotIn('goal',[e['type'] for e in self.simulate(world)['events']])

    def test_cpu_receivers_assign_air(self):
        record = json.loads((ROOT/'tests/fixtures/interactions/reception-record.json').read_text())
        # Give the CPU a useful, open passing option rather than forcing it to
        # throw through the stationary opponents in the animation fixture.
        for actor in record['initial']['entities']:
            actor['stats']['precision'] = 25
            if actor['team_id'] == 1:
                actor['position']['r'] = 8
        next(e for e in record['initial']['entities'] if e['id']==12)['position'] = {'q':4,'r':3}
        # Keep this passing situation the same distance from the corrected goal.
        for actor in record['initial']['entities']: actor['position']['q'] += 3
        response = self.engine.simulate(record['initial'], [None, None], 1, 12345, self.rules, (True, False))
        actions = response['orders'][0]['actions']
        throw = next(a for a in actions if a['action_type']=='throw')
        receiver = next(a for a in actions if a['entity_id']==throw['params']['target_entity_id'])
        self.assertGreaterEqual(receiver['params']['elements']['AIR'],1)

    def test_goal_line_configuration_changes_scoring(self):
        world = deepcopy(self.baseline)
        actor=world['entities'][0]; actor['position']={'q':11,'r':0}
        world['ball'].update(holder_entity_id=actor['id'],position=deepcopy(actor['position']))
        actor['status']['carrying_ball']=True
        self.assertNotIn('goal',[e['type'] for e in self.simulate(world)['events']])
        rules=deepcopy(self.rules);rules['simulation']['ball']['goal_line_half_width']=10
        self.assertIn('goal',[e['type'] for e in self.simulate(world,rules=rules)['events']])

    def test_placement_matches_reference_and_reflects_without_rotating(self):
        right = placement_zones(2)
        left = placement_zones(1)
        all_cells = set()
        for rz,lz in zip(right,left):
            self.assertIn(rz['defaultCell'],rz['cell'])
            cells={(c['x'],c['y']) for c in rz['cell']}
            self.assertFalse(cells & all_cells); all_cells |= cells
            self.assertEqual({(-x-y,y) for x,y in cells}, {(c['x'],c['y']) for c in lz['cell']})
        self.assertEqual(len(right[1]['cell']),48)
        self.assertEqual(len(right[3]['cell']),40)
        # The yellow back-right region includes the upper outer strip, above
        # the cyan back-left region; its small inner extension is also legal.
        yellow = {(p['x'] + p['y']//2, p['y']) for p in right[2]['cell']}
        self.assertTrue({(c,r) for c in range(8,12) for r in range(1,11)} <= yellow)
        self.assertEqual(placement_zones(1,2),right)
        self.assertEqual(placement_zones(2,2),left)
        self.assertTrue(all(c['y']>0 for c in right[1]['cell']))
        self.assertTrue(all(c['y']<0 for c in right[4]['cell']))
