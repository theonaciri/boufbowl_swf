"""Historical dependencies and explicit restoration choices, not historical odds."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from backend.engine import Engine
from backend.rulebook import rulebook_snapshot
from backend.turn_adapter import adapt_turn
from tests import test_backend as helpers
from tests import test_ball_attempts as ball_helpers
from tools.flash_protocol import Codec
from tools.game_config import ROOT, load_config


class RulebookSimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine=Engine(); cls.rules=load_config()['rules']
        cls.base=json.loads((ROOT/'tests/fixtures/movement_engine_turn.json').read_text())['initial']

    @classmethod
    def tearDownClass(cls): cls.engine.close()

    def simulate(self,world,actions,other=None,rules=None,seed=12345):
        orders=[dict(player_id=str(team),team_index=team,turn_number=1,nonce='rulebook',actions=orders)
                for team,orders in enumerate((actions,other or []))]
        response=self.engine.simulate(world,orders,1,seed,rules or self.rules,(False,False))
        return dict(initial=world,orders=response['orders'],result=response['result'],rules=rules or self.rules)

    def world(self):
        world=deepcopy(self.base)
        world['entities']=[world['entities'][0],world['entities'][5]]
        for i,e in enumerate(world['entities']):
            e.update(position=dict(q=i,r=0),hp=16,max_hp=16,ability_uses_remaining=2)
            e.pop('precise_position',None)
            e['status']=dict(stunned=False,knocked_down=False,carrying_ball=False)
        world['ball']=dict(position=dict(q=0,r=0),holder_entity_id=None,in_flight=False)
        return world

    def order(self,entity,kind='wait',elements=None,**params):
        return dict(entity_id=entity['id'],action_type=kind,params=dict(
            elements=elements or dict(TERRE=3,FEU=0,AIR=0,EAU=0),**params))

    def test_c06_water_characteristic_and_orders_reduce_risk_with_one_shared_draw(self):
        results=[]
        for water in (0,20):
            world=self.world();world['entities']=world['entities'][:1]
            actor=world['entities'][0];actor['stats']['endurance']=water
            record=self.simulate(world,[self.order(actor,'move',target_position=dict(q=4,r=0))])
            results.append(next(e['params'] for e in record['result']['events'] if e['type']=='movement_test'))
        self.assertGreater(results[0]['probability'],results[1]['probability'])
        self.assertEqual(results[0]['random_draw'],results[1]['random_draw'])
        self.assertGreater(results[1]['probability'],0)  # green is not guaranteed
        # Forced policy control proves a fall can happen in the reference zone.
        rules=deepcopy(self.rules);rules['simulation']['rulebook']['movement'].update(safe_failure=1,water_stat=0,water_order=0)
        world=self.world();world['entities']=world['entities'][:1];actor=world['entities'][0]
        record=self.simulate(world,[self.order(actor,'move',target_position=dict(q=2,r=0))],rules=rules)
        self.assertTrue(any(e['type']=='fall' for e in record['result']['events']))
        self.assertEqual(record['result'],self.simulate(world,record['orders'][0]['actions'],rules=rules)['result'])

    def test_c10_allies_and_enemies_both_increase_pickup_difficulty(self):
        chances=[]
        for team in (None,0,1):
            world=self.world();actor=world['entities'][0]
            if team is None:world['entities']=world['entities'][:1]
            else:world['entities'][1]['team_id']=team
            rules=deepcopy(self.rules);rules['simulation']['combat']['trigger_distance_cells']=.01
            record=self.simulate(world,[self.order(actor,elements=dict(TERRE=0,FEU=1,AIR=0,EAU=2))],rules=rules)
            attempt=next(e['params'] for e in record['result']['events'] if e['type'] in ('pickup','pickup_fail'))
            chances.append(attempt['pickup_chance'])
        self.assertGreater(chances[0],chances[1]);self.assertEqual(chances[1],chances[2])

    def test_c08_c09_targeting_changes_damage_and_stun_is_not_down(self):
        for targeted in (False,True):
            world=self.world();winner,loser=world['entities']
            winner['stats']['strength']=20;loser['stats']['strength']=10
            action=self.order(winner,'follow',target_entity_id=loser['id']) if targeted else self.order(winner)
            record=self.simulate(world,[action],[self.order(loser)])
            damage=next(e for e in record['result']['events'] if e['type']=='damage')
            self.assertEqual(damage['params']['damage'],1 if targeted else 0)
            self.assertTrue(any(e['type']=='stun' for e in record['result']['events']))
            self.assertFalse(any(e['type']=='ko' for e in record['result']['events']))
            scenario=adapt_turn(record);Codec().encode('ResolutionScenarioMessage',scenario)
            fight=next(e['interactionDetails'] for e in scenario['interaction'] if e['interactionDetails']['type']==20)
            self.assertEqual(fight['fightTest']['outcome'],3)
            self.assertTrue(any(p['status']==2 for p in next(e for e in scenario['interaction'] if e['interactionDetails']['type']==20)['interactionDetails']['participants']))

    def test_c11_combat_loss_penalizes_later_pickup_in_same_turn(self):
        world=self.world();collector,enemy=world['entities']
        collector['stats']['strength']=5;enemy['stats']['strength']=20
        own=self.order(collector,elements=dict(TERRE=0,FEU=1,AIR=0,EAU=2))
        record=self.simulate(world,[own],[self.order(enemy)])
        event=next(e for e in record['result']['events'] if e['type'] in ('pickup','pickup_fail'))
        self.assertEqual(event['params']['lost_combats'],1)
        rules=deepcopy(self.rules);rules['simulation']['combat']['trigger_distance_cells']=.01
        control=self.simulate(world,[own],[self.order(enemy)],rules)
        plain=next(e for e in control['result']['events'] if e['type'] in ('pickup','pickup_fail'))
        self.assertGreater(plain['params']['pickup_chance'],event['params']['pickup_chance'])

    def test_c17_water_stun_recovery_can_precede_airborne_reception(self):
        for water,catches in ((0,False),(20,True)):
            world=self.world();passer,receiver=world['entities']
            receiver.update(team_id=0,position=dict(q=6,r=0));receiver['stats']['endurance']=water
            receiver['status']['stunned']=True;passer['status']['carrying_ball']=True
            world['ball']['holder_entity_id']=passer['id']
            rules=deepcopy(self.rules);rules['simulation']['simulation'].update(probability_min=1,probability_max=1)
            air=dict(TERRE=0,FEU=0,AIR=3,EAU=0)
            record=self.simulate(world,[self.order(passer,'throw',air,target_entity_id=receiver['id']),self.order(receiver,elements=air)],rules=rules)
            caught=[e for e in record['result']['events'] if e['type']=='catch']
            self.assertEqual(bool(caught),catches)
            Codec().encode('ResolutionScenarioMessage',adapt_turn(record))

    def test_policy_snapshot_is_frozen_complete_and_identified(self):
        snapshot=rulebook_snapshot(self.rules)
        self.assertEqual({r['id'] for r in snapshot['rules']},{f'C{i:02}' for i in range(1,23)})
        changed=deepcopy(self.rules);changed['simulation']['rulebook']['pickup']['radius']=2
        self.assertNotEqual(snapshot['sha256'],rulebook_snapshot(changed)['sha256'])
        self.assertEqual(snapshot,rulebook_snapshot(self.rules))
        legacy=deepcopy(self.rules);legacy['simulation'].pop('rulebook')
        self.assertIsNone(rulebook_snapshot(legacy))

    def test_protection_abilities_absorb_damage_without_permanent_hp_or_revival(self):
        for protection in ('shield','temporary_hp'):
            world=self.world();caster,enemy=world['entities']
            caster.update(class_name='Feca',position=dict(q=-6,r=0))
            ally=deepcopy(caster);ally.update(id=99,position=dict(q=0,r=0),class_name='Iop')
            ally['stats']['strength']=1;enemy['stats']['strength']=50
            world['entities'].append(ally)
            rules=deepcopy(self.rules)
            rules['abilities']['Feca']=dict(name='Feca',verified=False,target='allies',**{protection:4})
            record=self.simulate(world,[dict(entity_id=caster['id'],action_type='ability',params={}),self.order(ally)],
                                 [self.order(enemy)],rules)
            damage=next(e['params'] for e in record['result']['events'] if e['type']=='damage')
            self.assertEqual(damage['damage'],0)
            self.assertEqual(damage['absorbed_shield' if protection=='shield' else 'absorbed_temporary'],4)
            self.assertTrue(all(e['hp']==16 for e in record['result']['final_world_state']['entities']))
            self.assertTrue(all('shield_hp' not in e and 'temporary_hp' not in e for e in record['result']['final_world_state']['entities']))
            Codec().encode('ResolutionScenarioMessage',adapt_turn(record))

    def test_stun_remainder_survives_turn_boundary_and_eventually_recovers(self):
        world=self.world();winner,loser=world['entities']
        winner['stats']['strength']=20;loser['stats'].update(strength=10,endurance=0)
        rules=deepcopy(self.rules);rules['simulation']['tick_system']['max_ticks_per_turn']=5
        first=self.simulate(world,[self.order(winner)],[self.order(loser)],rules)['result']['final_world_state']
        stunned=next(e for e in first['entities'] if e['id']==loser['id'])
        self.assertTrue(stunned['status']['stunned']);self.assertGreater(stunned['stun_ticks_remaining'],0)
        first['entities']=[stunned]
        recovered=self.simulate(first,[],[self.order(stunned)])['result']
        self.assertTrue(any(e['type']=='stun_end' for e in recovered['events']))
        self.assertFalse(recovered['final_world_state']['entities'][0]['status']['stunned'])

    def passing_world(self):
        world=self.world();passer,receiver=world['entities'];receiver['team_id']=0
        receiver['position']=dict(q=6,r=0);passer['status']['carrying_ball']=True
        world['ball']['holder_entity_id']=passer['id']
        return world,passer,receiver

    def test_air_orders_speed_flight_and_failed_tests_scatter_on_trajectory(self):
        air=dict(TERRE=0,FEU=0,AIR=3,EAU=0);landings=[]
        for bonus in (0,.1):
            world,passer,receiver=self.passing_world();rules=deepcopy(self.rules)
            rules['simulation']['rulebook']['passing']['air_speed_bonus']=bonus
            rules['simulation']['simulation'].update(probability_min=1,probability_max=1)
            record=self.simulate(world,[self.order(passer,'throw',air,target_entity_id=receiver['id']),self.order(receiver,elements=air)],rules=rules)
            landings.append(next(e['params']['land_tick'] for e in record['result']['events'] if e['type']=='throw'))
        self.assertGreater(landings[0],landings[1])
        for throw_succeeds in (False,True):
            world,passer,receiver=self.passing_world();rules=deepcopy(self.rules)
            rules['simulation']['simulation'].update(probability_min=0,probability_max=1,throw_base=int(throw_succeeds),throw_stat=0,distance_penalty=0,catch_base=0,catch_stat=0,catch_air=0,catch_feu=0)
            rules['simulation']['probabilities']['air_precision_per_action']=0
            record=self.simulate(world,[self.order(passer,'throw',air,target_entity_id=receiver['id']),self.order(receiver,elements=air)],rules=rules)
            landed=next(e['params']['position'] for e in record['result']['events'] if e['type']=='ball_land')
            self.assertEqual(landed['r'],0);self.assertGreaterEqual(landed['q'],0);self.assertLessEqual(landed['q'],6)
            self.assertFalse(any(e['type']=='catch' for e in record['result']['events']))
            Codec().encode('ResolutionScenarioMessage',adapt_turn(record))

    def test_converging_pass_waits_and_diverging_pass_starts_early(self):
        air=dict(TERRE=0,FEU=0,AIR=3,EAU=0);ticks=[]
        for destination in (3,9):
            world,passer,receiver=self.passing_world();rules=deepcopy(self.rules)
            rules['simulation']['simulation'].update(probability_min=1,probability_max=1)
            record=self.simulate(world,[self.order(passer,'throw',air,target_entity_id=receiver['id']),
                self.order(receiver,'move',air,target_position=dict(q=destination,r=0))],rules=rules)
            ticks.append(next(e['tick'] for e in record['result']['events'] if e['type']=='throw'))
        self.assertGreater(ticks[0],ticks[1])

    def test_c16_behind_passer_adjacency_alone_does_not_intercept(self):
        world,passer,receiver=self.passing_world()
        behind=deepcopy(receiver);behind.update(id=99,team_id=1,position=dict(q=-1,r=0));world['entities'].append(behind)
        rules=deepcopy(self.rules);rules['simulation']['combat']['trigger_distance_cells']=.01
        rules['simulation']['simulation'].update(probability_min=1,probability_max=1)
        rules['simulation']['ball']['intercept_height_threshold']=10
        air=dict(TERRE=0,FEU=0,AIR=3,EAU=0);fire=dict(TERRE=0,FEU=3,AIR=0,EAU=0)
        record=self.simulate(world,[self.order(passer,'throw',air,target_entity_id=receiver['id']),self.order(receiver,elements=air)],
                             [self.order(behind,elements=fire)],rules)
        self.assertFalse(any(e['type'] in ('catch','catch_fail') and e['actor']==99 for e in record['result']['events']))
        self.assertTrue(any(e['type']=='catch' and e['actor']==receiver['id'] for e in record['result']['events']))

    def test_disputed_critical_dodge_down_and_ball_drop_are_separate_policy(self):
        for knockdown in (False,True):
            world=self.world();attacker,defender=world['entities']
            attacker['stats'].update(strength=30,agility=1);defender['stats'].update(strength=10,agility=80)
            attacker['status']['carrying_ball']=True;world['ball']['holder_entity_id']=attacker['id']
            rules=deepcopy(self.rules);rules['simulation']['rulebook']['combat']['critical_dodge_down']=knockdown
            record=self.simulate(world,[self.order(attacker,elements=dict(TERRE=0,FEU=0,AIR=3,EAU=0))],
                                 [self.order(defender,elements=dict(TERRE=0,FEU=3,AIR=0,EAU=0))],rules)
            duel=next(e['params'] for e in record['result']['events'] if e['type']=='dodge')
            self.assertEqual((duel['tier'],duel['branch'],duel['loser']),('critical','dodge',attacker['id']))
            self.assertEqual(any(e['type']=='ko' and e['actor']==attacker['id'] for e in record['result']['events']),knockdown)
            self.assertEqual(any(e['type']=='ball_drop' and e['actor']==attacker['id'] for e in record['result']['events']),knockdown)
            Codec().encode('ResolutionScenarioMessage',adapt_turn(record))

    def test_unresolved_tier_equalities_follow_explicit_configured_choice(self):
        for margin,lower,upper in ((0,'normal','normal'),(15,'normal','wide'),(30,'wide','critical')):
            for boundary,expected in (('lower',lower),('upper',upper)):
                world=self.world();winner,loser=world['entities']
                winner['stats']['strength']=10+margin;loser['stats']['strength']=10
                rules=deepcopy(self.rules);rules['simulation']['rulebook']['combat']['boundary']=boundary
                record=self.simulate(world,[self.order(winner)],[self.order(loser)],rules)
                event=next(e for e in record['result']['events'] if e['type']=='duel')
                self.assertEqual(event['params']['tier'],expected)

    def test_wide_win_bonus_is_used_by_next_combat_and_expires(self):
        world=self.world();winner,first=world['entities']
        winner['stats']['strength']=40;first['stats']['strength']=20
        second=deepcopy(first);second.update(id=99,position=dict(q=0,r=-1));second['stats']['strength']=40
        world['entities'].append(second)
        margins=[]
        for bonus in (0,1):
            rules=deepcopy(self.rules);rules['simulation']['rulebook']['combat']['next_bonus']=bonus
            record=self.simulate(world,[self.order(winner)],[self.order(first),self.order(second)],rules)
            fights=[e for e in record['result']['events'] if e['type']=='duel']
            self.assertEqual(fights[0]['params']['tier'],'wide')
            margins.append(fights[1]['params']['margin'])
            self.assertTrue(all('next_combat_bonus' not in e for e in record['result']['final_world_state']['entities']))
            scenario=adapt_turn(record)
            journal=[item['interactionDetails']['fightTest'] for item in scenario['interaction'] if item['interactionDetails']['type']==20]
            self.assertEqual(abs(journal[1]['score'][0]['finalScore']-journal[1]['score'][1]['finalScore']),fights[1]['params']['margin'])
        self.assertGreater(margins[1],margins[0])


class RulebookConnectionTests(unittest.TestCase):
    setUp=helpers.BackendTests.setUp
    tearDown=helpers.BackendTests.tearDown
    command=helpers.BackendTests.command
    protocol=helpers.BackendTests.protocol
    identity=helpers.BackendTests.identity
    start=helpers.BackendTests.start

    def test_c22_grace_keeps_progress_and_reconnects_same_match(self):
        self.start();profile=self.identity(self.alice)
        match=self.service.store.active_match(profile);now=match['created']
        with patch('backend.service.time.time',return_value=now+40):
            with self.service.store.transaction():
                self.assertFalse(self.service.check_reconnections(match))
                self.assertEqual(match['phase'],'orders')
                match['pending']=dict(final_world_state=deepcopy(match['world']),score=[0,0])
                self.service.advance(match);self.service.store.save_match(match)
            response=self.service.hello(dict(session=self.alice['session']))
            self.assertEqual(response['current_match'],str(match['id']))
            restored=self.service.store.active_match(profile)
            self.assertEqual(restored['turn'],2)
            self.assertEqual(restored['disconnected'],{})

    def test_c22_expiry_and_late_heartbeat_cannot_resurrect_match(self):
        match=self.start();now=match['created']
        self.service.store.db.execute('UPDATE presence SET seen=? WHERE profile_id=?',(now,self.identity(self.alice)))
        with patch('backend.service.time.time',return_value=now+150):
            response=self.service.hello(dict(session=self.alice['session']))
            self.assertIsNone(response['current_match'])
            ended=self.service.store.match(match['id'])
            self.assertEqual(ended['end_reason'],'disconnect_timeout')
            self.assertEqual(ended['given_up'],1)
            self.assertEqual(ended['phase'],'ended')

    def test_legacy_match_has_no_new_disconnect_policy(self):
        match=self.start();match['rules']['simulation'].pop('rulebook')
        with patch('backend.service.time.time',return_value=match['created']+9999):
            self.assertFalse(self.service.check_reconnections(match))
        self.assertNotEqual(match['phase'],'ended')

    def test_both_disconnected_uses_documented_existing_score_policy(self):
        with self.service.store.transaction():
            match=self.service.create_match(self.identity(self.alice),self.identity(self.bob),1)
            match['score']=[2,1]
            for profile in match['profiles']:
                self.service.store.db.execute('UPDATE presence SET seen=? WHERE profile_id=?',(match['created'],profile))
            with patch('backend.service.time.time',return_value=match['created']+150):
                self.assertTrue(self.service.check_reconnections(match))
            self.assertEqual(match['end_reason'],'both_disconnected')
            self.assertEqual(match['score'],[2,1])
            self.assertIsNone(match['given_up'])

    def test_match_keeps_rulebook_snapshot_after_default_policy_changes(self):
        match=self.start();frozen=deepcopy(match['rulebook'])
        self.service.config['rules']['simulation']['rulebook']['pickup']['radius']=2
        self.assertEqual(match['rulebook'],frozen)
        self.assertNotEqual(frozen['sha256'],rulebook_snapshot(self.service.config['rules'])['sha256'])
        self.protocol(self.alice,'ORDERS',dict(turn=1,orders=[]))
        record=json.loads(self.service.store.db.execute('SELECT record_json FROM turns WHERE match_id=?',(match['id'],)).fetchone()[0])
        self.assertEqual(record['rulebook']['sha256'],frozen['sha256'])
        from backend.replay import export_replay
        replay=export_replay(self.service,match['id'])
        self.assertEqual(replay['rulebook'],frozen)
        self.assertEqual(replay['records'],[])  # active exports still hide seeds/orders


if __name__=='__main__':unittest.main()
