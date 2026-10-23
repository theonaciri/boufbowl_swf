"""Deterministic checks for supported forum semantics, not missing formulas.

Evidence codes refer to docs/RECOVERED_RULES.md and preservation commit 484d203.
Legacy configurations are separate controls, never evidence for historical odds.
"""
from copy import deepcopy
import unittest

from backend.storage import ServiceError
from backend.turn_adapter import adapt_turn
from tests import test_backend as service_helpers
from tests import test_ball_attempts as ball_helpers
from tests import test_class_powers as power_helpers
from tools.power_descriptions import client_abilities


class RecoveredServerRulesTests(unittest.TestCase):
    setUp = service_helpers.BackendTests.setUp
    tearDown = service_helpers.BackendTests.tearDown
    command = service_helpers.BackendTests.command
    protocol = service_helpers.BackendTests.protocol
    identity = service_helpers.BackendTests.identity
    start = service_helpers.BackendTests.start

    def test_c01_role_limit_counts_whole_roster_across_classes(self):
        club = service_helpers.initial_club()
        for player, cls in zip(club['boufbowler'], (6, 6, 8, 8, 1, 4, 13, 2, 3, 11)):
            player['boufbowlerClass'] = cls
        with self.assertRaises(ServiceError) as raised:
            self.service.normalize_club(club)
        self.assertEqual(raised.exception.code, 'ROSTER_ROLE_LIMIT')
        # Three Iops are legal: class duplication is not the restriction.
        for player, cls in zip(club['boufbowler'], (6, 6, 6, 1, 4, 13, 2, 3, 11, 5)):
            player['boufbowlerClass'] = cls
        self.assertEqual(len(self.service.normalize_club(club)['boufbowler']), 10)
        legacy = deepcopy(self.config['rules'])
        legacy['match'].pop('roster_role_limit')
        self.service.validate_roster_roles([dict(boufbowlerClass=6)] * 10, legacy)

    def test_c01_saved_old_club_cannot_bypass_new_match_role_policy(self):
        profile = self.identity(self.alice)
        collection = self.service.collection(profile)
        for player in collection['clubs'][collection['active']]['boufbowler']:
            player['boufbowlerClass'] = 6
        self.service.store.save_club(profile, collection)
        with self.assertRaises(ServiceError) as raised:
            self.command(self.alice, 'cpu_match', stadium=1)
        self.assertEqual(raised.exception.code, 'ROSTER_ROLE_LIMIT')
        self.assertIsNone(self.service.store.active_match(profile))

    def test_legacy_inactive_gallery_does_not_block_first_login(self):
        starter = service_helpers.initial_club()
        gallery = deepcopy(starter)
        gallery['clubId'] = '2'
        for player in gallery['boufbowler']:
            player['boufbowlerClass'] = 6
        newcomer = self.service.hello(dict(nickname='Gallery Check', clubs=[starter, gallery]))
        profile = self.identity(newcomer)
        self.assertEqual(len(self.service.collection(profile)['clubs']), 2)
        with self.assertRaises(ServiceError):
            self.command(newcomer, 'cpu_match', club_id='2', stadium=1)

    def test_c05_only_resting_reserves_heal_and_charges_do_not_refill(self):
        match = self.start()
        field = [e for e in match['world']['entities'] if e['team_id'] == 0]
        field[0].update(hp=5, ability_uses_remaining=0)
        field[1]['hp'] = 0
        reserve = match['rosters'][0]['characters'][5]
        match['roster_health'] = {reserve['id']: 4}
        self.service.reset_round(match)
        self.assertEqual(field[0]['hp'], 5)  # reset must not destroy old HP
        zones = self.service.match_information(match, 1)['placementZone']
        selected = match['rosters'][0]['characters'][:5]
        selected[-1] = reserve
        match['placements']['1'] = [dict(id=p['id'], position=z['defaultCell']) for p, z in zip(selected, zones)]
        self.service.finish_placement(match)
        by_id = {e['id']: e for e in match['world']['entities']}
        self.assertEqual(by_id[field[0]['id']]['hp'], 5)
        self.assertEqual(by_id[field[0]['id']]['ability_uses_remaining'], 0)
        self.assertEqual(by_id[int(reserve['id'])]['hp'], by_id[int(reserve['id'])]['max_hp'])
        self.assertEqual(by_id[field[1]['id']]['hp'], 0)
        self.assertTrue(by_id[field[1]['id']]['status']['knocked_down'])
        self.assertEqual(len(match['world']['entities']), 10)

    def test_dead_reserve_does_not_implicitly_revive_after_benching(self):
        match = self.start()
        dead = match['world']['entities'][0]
        dead['hp'] = 0
        self.service.reset_round(match)
        roster = match['rosters'][0]['characters']
        zones = self.service.match_information(match, 1)['placementZone']
        match['placements']['1'] = [dict(id=p['id'], position=z['defaultCell']) for p, z in zip(roster[5:], zones)]
        self.service.finish_placement(match)
        self.service.reset_round(match, receiving_side=1)
        self.service.finish_placement(match)  # defaults put the former starters back
        restored = next(e for e in match['world']['entities'] if e['id'] == dead['id'])
        self.assertEqual(restored['hp'], 0)
        self.assertNotEqual(match['world']['ball']['holder_entity_id'], dead['id'])

    def test_c05_legacy_snapshot_keeps_full_field_healing(self):
        match = self.start()
        match['rules']['match'].pop('restart_recovery')
        match['world']['entities'][0]['hp'] = 5
        self.service.reset_round(match)
        self.service.finish_placement(match)
        self.assertTrue(all(e['hp'] == e['max_hp'] for e in match['world']['entities']))

    def test_c19_fifth_touchdown_does_not_end_match_before_allotted_turns(self):
        match = self.start()
        match['score'] = [4, 0]
        match['pending'] = dict(final_world_state=deepcopy(match['world']), score=[1, 0])
        self.service.advance(match)
        self.assertEqual(match['score'], [5, 0])
        self.assertEqual(match['phase'], 'placement')


class RecoveredBallRulesTests(unittest.TestCase):
    setUpClass = classmethod(ball_helpers.BallAttemptTests.setUpClass.__func__)
    tearDownClass = classmethod(ball_helpers.BallAttemptTests.tearDownClass.__func__)
    world = ball_helpers.BallAttemptTests.world
    run_turn = ball_helpers.BallAttemptTests.run_turn
    fixed_chance = ball_helpers.BallAttemptTests.fixed_chance
    successful_throw_failed_catches = ball_helpers.BallAttemptTests.successful_throw_failed_catches

    def test_c14_arrival_boundary_and_legacy_control(self):
        # Six cells at eight cells/s and 0.1s/tick: 8 flight ticks, release 1.
        for maximum, enabled, launches in ((9, True, False), (10, True, True), (9, False, True)):
            with self.subTest(maximum=maximum, enabled=enabled):
                rules = self.fixed_chance(1)
                rules['simulation']['tick_system']['max_ticks_per_turn'] = maximum
                rules['simulation']['ball']['require_arrival_before_turn_end'] = enabled
                world = self.world(passing=True)
                record = self.run_turn(world, [(3, 0), (3, 0)], rules, passing=True)
                result = record['result']
                self.assertEqual(any(e['type'] == 'throw' for e in result['events']), launches)
                if not launches:
                    self.assertFalse(any(e['type'] in ('ball_move', 'ball_land', 'catch') for e in result['events']))
                    self.assertEqual(result['final_world_state']['ball']['holder_entity_id'], world['entities'][0]['id'])
                # Repeated runs have identical seeds/outcomes; no hidden timer.
                self.assertEqual(result, self.run_turn(world, [(3, 0), (3, 0)], rules, passing=True)['result'])

    def test_fire_interception_uses_agility_and_reception_keeps_precision(self):
        for agility, precision, historical in ((2, 19, True), (19, 2, True), (2, 19, False)):
            with self.subTest(agility=agility, precision=precision, historical=historical):
                world = self.world(passing=True, interceptor=True)
                world['entities'][2]['stats'].update(agility=agility, precision=precision)
                rules = self.successful_throw_failed_catches()
                rules['simulation']['simulation'].update(catch_stat=.03, catch_feu=.1)
                rules['simulation']['ball']['interception_uses_fire_stat'] = historical
                record = self.run_turn(world, [(3, 0), (3, 0), (0, 1)], rules, passing=True)
                interceptor = world['entities'][2]['id']
                event = next(e for e in record['result']['events'] if e['type'] in ('catch', 'catch_fail') and e['actor'] == interceptor)
                self.assertAlmostEqual(event['params']['catch_chance'], (agility if historical else precision) * .03 + .1)

    def test_c15_contact_before_launch_interrupts_throw_without_dropping_ball(self):
        for cancels in (True, False):
            world = self.world(passing=True, interceptor=True)
            passer = world['entities'][0]
            passer['stats']['strength'] = 1
            world['entities'][2]['stats']['strength'] = 20
            rules = self.fixed_chance(1)
            rules['simulation']['ball']['contact_cancels_pending_throw'] = cancels
            rules['simulation']['combat'].update(trigger_distance_cells=1.01)
            rules['simulation']['combat']['duel']['damage_on_win'] = 0
            rules['simulation']['simulation'].update(fall_base=0, fall_per_power=0, fall_max=0)
            # run_turn normally disables combat to isolate ball tests.
            actions = [[], []]
            for entity, air in zip(world['entities'], (3, 3, 0)):
                actions[entity['team_id']].append(dict(entity_id=entity['id'], action_type='wait',
                    params=dict(elements=dict(TERRE=0, FEU=0, AIR=air, EAU=3-air))))
            actions[0].append(dict(entity_id=passer['id'], action_type='throw',
                params=dict(elements=actions[0][0]['params']['elements'], target_entity_id=world['entities'][1]['id'])))
            orders = [dict(player_id=str(team), turn_number=1, team_index=team, nonce='contact', actions=actions[team]) for team in (0, 1)]
            result = self.engine.simulate(world, orders, 1, 12345, rules, (False, False))['result']
            self.assertTrue(any(e['type'] == 'duel' for e in result['events']))
            self.assertEqual(any(e['type'] == 'throw' for e in result['events']), not cancels)
            if cancels:
                self.assertEqual(result['final_world_state']['ball']['holder_entity_id'], passer['id'])
                cancelled = [e for e in result['events'] if e['type'] == 'throw_cancelled']
                self.assertEqual(len(cancelled), 1)
                self.assertEqual(cancelled[0]['params']['reason'], 'contact')

    def test_c07_zero_water_never_stands_but_one_water_does(self):
        for water in (0, 1):
            world = self.world()
            world['entities'][0]['status']['knocked_down'] = True
            record = self.run_turn(world, [(3-water, 0)])
            self.assertEqual(any(e['type'] == 'stand_up' for e in record['result']['events']), bool(water))
            self.assertEqual(record['result']['final_world_state']['entities'][0]['status']['knocked_down'], not bool(water))

    def test_c13_preassigned_onward_pass_chains_after_receiving_possession(self):
        world = self.world(passing=True)
        third = deepcopy(world['entities'][1])
        third['id'] = 13
        third['position'] = dict(q=6, r=0)
        world['entities'][1]['position'] = dict(q=3, r=0)
        world['entities'].append(third)
        elements = dict(TERRE=0, FEU=0, AIR=3, EAU=0)
        actions = [dict(entity_id=e['id'], action_type='wait', params=dict(elements=elements)) for e in world['entities']]
        actions.extend(dict(entity_id=actor['id'], action_type='throw', params=dict(elements=elements, target_entity_id=target['id']))
                       for actor, target in zip(world['entities'], world['entities'][1:]))
        orders = [dict(player_id=str(team), turn_number=1, team_index=team, nonce='chain', actions=actions if team == 0 else []) for team in (0, 1)]
        rules = self.fixed_chance(1)
        rules['simulation']['ball']['catch_radius_cells'] = .01
        result = self.engine.simulate(world, orders, 1, 12345, rules, (False, False))['result']
        thrown = [e for e in result['events'] if e['type'] == 'throw']
        caught = [e for e in result['events'] if e['type'] == 'catch']
        self.assertEqual([e['actor'] for e in thrown], [world['entities'][0]['id'], world['entities'][1]['id']])
        self.assertEqual([e['actor'] for e in caught], [world['entities'][1]['id'], third['id']])
        self.assertGreater(thrown[1]['tick'], caught[0]['tick'])
        self.assertEqual(result['final_world_state']['ball']['holder_entity_id'], third['id'])


class RecoveredAbilityRulesTests(unittest.TestCase):
    setUpClass = classmethod(power_helpers.ClassPowerTests.setUpClass.__func__)
    tearDownClass = classmethod(power_helpers.ClassPowerTests.tearDownClass.__func__)
    world = power_helpers.ClassPowerTests.world
    run_power = power_helpers.ClassPowerTests.run_power

    def test_c18_ecaflip_redirects_enemy_heal_independent_of_actor_order(self):
        for ecaflip_first in (True, False):
            with self.subTest(ecaflip_first=ecaflip_first):
                world = self.world('Ecaflip' if ecaflip_first else 'Eniripsa')
                world['entities'][2]['class_name'] = 'Eniripsa' if ecaflip_first else 'Ecaflip'
                response = self.run_power(world, other=[dict(entity_id=3, action_type='ability', params={})])
                by_id = {e['id']: e for e in response['result']['final_world_state']['entities']}
                beneficiaries = (1, 2) if ecaflip_first else (3, 4)
                for identity, entity in by_id.items():
                    self.assertEqual(entity['hp'], 10 if identity in beneficiaries else 8)
                heal = next(e for e in response['result']['events'] if e['type'] == 'ability' and e['params']['name'] == 'Eniripsa')
                self.assertEqual(heal['params']['redirected_by'], 1 if ecaflip_first else 3)
                scenario = adapt_turn(dict(initial=world, orders=response['orders'], result=response['result'], rules=self.rules))
                # Actual wire serialization catches invalid class-order targets.
                from tools.flash_protocol import Codec
                Codec().encode('ResolutionScenarioMessage', scenario)

    def test_c18_no_enemy_heal_has_no_effect_and_never_resurrects(self):
        world = self.world('Ecaflip')
        world['entities'][1]['hp'] = 0
        result = self.run_power(world)['result']
        event = next(e for e in result['events'] if e['type'] == 'ability')
        self.assertEqual(event['params']['targets'], [])
        self.assertEqual(event['params']['redirected_healers'], [])
        self.assertEqual([e['hp'] for e in result['final_world_state']['entities']], [8, 0, 8, 8])
        self.assertEqual(result['final_entity_states'][0]['ability_uses_remaining'], 1)
        self.assertNotIn('random_draw', event['params'])
        descriptions = client_abilities(self.rules)['Ecaflip']['descriptions']
        self.assertIn('aucun effet', descriptions['fr'])
        self.assertNotIn('50%', descriptions['fr'])

    def test_c18_redirected_heal_skips_dead_and_clamps_living_hp(self):
        world = self.world('Ecaflip')
        world['entities'][0]['hp'] = 15
        world['entities'][1]['hp'] = 0
        world['entities'][2]['class_name'] = 'Eniripsa'
        response = self.run_power(world, other=[dict(entity_id=3, action_type='ability', params={})])
        self.assertEqual([e['hp'] for e in response['result']['final_world_state']['entities']], [16, 0, 8, 8])


if __name__ == '__main__':
    unittest.main()
