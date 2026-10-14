from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest

from backend.service import Service
from backend.storage import ServiceError
from tools.build_mock_fixture import build_fixture
from tools.game_config import load_config


def initial_club():
    roster = build_fixture()["steps"][0]["decoded"]["leftRoster"]
    return {"clubId": "1", "clubName": "Test Club", "boufbowler": roster["characters"], "paletteId": 1,
            "firstColor": roster["firstColor"], "secondColor": roster["secondColor"], "patternColor": roster["patternColor"],
            "sigilBackground": 1, "sigilCharge": 1, "isPredefinedClub": False}


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "state.sqlite"
        self.config = load_config()
        self.config["rules"]["match"].update(turns_per_match=2, turns_per_period=2)
        self.service = Service(self.path, self.config)
        self.alice = self.service.hello({"nickname": "Alice", "clubs": [initial_club()]})
        self.bob = self.service.hello({"nickname": "Bob", "clubs": [initial_club()]})
        self.sequence = 0

    def tearDown(self):
        self.service.close()
        self.directory.cleanup()

    def command(self, player, operation="protocol", **payload):
        self.sequence += 1
        return self.service.command({"session": player["session"], "request_id": str(self.sequence), "operation": operation, **payload})

    def protocol(self, player, name, payload):
        return self.command(player, hex=self.service.codec.envelope(name, payload).hex())

    def identity(self, player):
        return self.service.store.authenticate(player["session"])

    def start(self):
        self.command(self.alice, "cpu_match", stadium=1)
        match = self.service.store.active_match(self.identity(self.alice))
        zones = self.service.match_information(match, 1)["placementZone"]
        positions = [{"id": p["id"], "position": z["defaultCell"]} for p, z in zip(match["rosters"][0]["characters"][:5], zones)]
        self.protocol(self.alice, "PLACEMENT", {"turn": 1, "boufbowlerPositions": positions})
        return match

    def test_club_customization_is_owned_and_survives_restart(self):
        club = initial_club()
        club["clubName"] = "Persistent club"
        club["boufbowler"][0]["boufbowlerClass"] = 1
        club["boufbowler"][0]["attributes"]["earth"] = 999
        self.command(self.alice, "save_club", club=club)
        self.service.close()
        self.service = Service(self.path, self.config)
        response = self.service.hello({"session": self.alice["session"]})
        stored = self.service.club(self.identity(self.alice))
        self.assertEqual(stored["clubName"], "Persistent club")
        self.assertEqual(stored["boufbowler"][0]["attributes"]["earth"], self.config["rules"]["classes"]["defaults"]["earth"])
        self.assertEqual(response["profile"]["nickname"], "Alice")
        self.assertEqual(self.service.club(self.identity(self.bob))["clubName"], "Test Club")

    def test_invalid_session_and_player_ownership_are_rejected(self):
        with self.assertRaisesRegex(ServiceError, "session"):
            self.service.poll({"session": "not-a-valid-session-token", "cursor": 0})
        self.start()
        with self.assertRaisesRegex(ServiceError, "own active"):
            self.protocol(self.alice, "ORDERS", {"turn": 1, "orders": [{"boufbowlerId": "101", "regularOrder": {"elements": [4, 4, 4]}}]})

    def test_command_retries_do_not_create_duplicate_matches(self):
        body = {"session": self.alice["session"], "request_id": "same-request", "operation": "cpu_match", "stadium": 1}
        first = self.service.command(body)
        self.assertEqual(self.service.command(body), first)
        self.assertEqual(self.service.store.db.execute("SELECT COUNT(*) FROM matches").fetchone()[0], 1)
        with self.assertRaisesRegex(ServiceError, "reused"):
            self.service.command({**body, "stadium": 6})

    def test_cpu_match_completes_and_rewards_are_recorded_once(self):
        self.start()
        for turn in (1, 2):
            self.protocol(self.alice, "ORDERS", {"turn": turn, "orders": []})
            match = self.service.store.active_match(self.identity(self.alice))
            self.assertEqual(match["phase"], "resolution")
            self.service.codec.envelope("RESOLUTION_SCENARIO", match["scenario"])
            self.protocol(self.alice, "RESOLUTION_DONE", {"turn": turn})
        self.assertIsNone(self.service.store.active_match(self.identity(self.alice)))
        self.assertEqual(self.service.store.db.execute("SELECT COUNT(*) FROM match_results").fetchone()[0], 1)
        self.assertEqual(self.service.store.db.execute("SELECT COUNT(*) FROM turns").fetchone()[0], 2)
        stats = self.service.store.profile(self.identity(self.alice))["statistics"]
        self.assertEqual(stats["wins"] + stats["draws"] + stats["defeats"], 1)

    def test_resolution_checkpoint_restores_initial_state_and_scenario(self):
        self.start()
        self.protocol(self.alice, "ORDERS", {"turn": 1, "orders": []})
        before = self.service.store.active_match(self.identity(self.alice))
        self.service.close()
        self.service = Service(self.path, self.config)
        resumed = self.service.hello({"session": self.alice["session"]})
        events = self.service.poll({"session": self.alice["session"], "cursor": resumed["cursor"]})["events"]
        self.assertEqual([e["type"] for e in events][-3:], ["MATCH_INFORMATION", "FIELD_STATE", "RESOLUTION_SCENARIO"])
        self.assertEqual(self.service.store.active_match(self.identity(self.alice))["world"], before["world"])
        self.protocol(self.alice, "RESOLUTION_DONE", {"turn": 1})
        self.assertEqual(self.service.store.active_match(self.identity(self.alice))["turn"], 2)

    def test_deadlines_select_defaults_and_resolve_without_client_commands(self):
        self.command(self.alice, "cpu_match", stadium=1)
        with self.service.store.transaction():
            match = self.service.store.active_match(self.identity(self.alice))
            match["deadline"] = time.time() - 1
            self.service.store.save_match(match)
        self.service.poll({"session": self.alice["session"], "cursor": 0})
        with self.service.store.transaction():
            match = self.service.store.active_match(self.identity(self.alice))
            self.assertEqual(match["phase"], "orders")
            match["deadline"] = time.time() - 1
            self.service.store.save_match(match)
        self.service.poll({"session": self.alice["session"], "cursor": 0})
        self.assertEqual(self.service.store.active_match(self.identity(self.alice))["phase"], "resolution")

    def test_challenge_requires_guest_acceptance_and_creates_human_match(self):
        self.protocol(self.alice, "MATCH_REQUEST", {"challenge": {"guestNickname": "Bob", "matchStadium": 1}})
        offer = self.service.store.db.execute("SELECT id FROM challenges").fetchone()[0]
        with self.assertRaisesRegex(ServiceError, "challenged player"):
            self.protocol(self.alice, "CHALLENGE_ANSWER", {"offerId": offer, "answer": 2})
        self.protocol(self.bob, "CHALLENGE_ANSWER", {"offerId": offer, "answer": 2})
        match = self.service.store.active_match(self.identity(self.alice))
        self.assertEqual(match["profiles"], [self.identity(self.alice), self.identity(self.bob)])
        self.assertEqual(self.service.store.active_match(self.identity(self.bob))["id"], match["id"])

    def test_human_match_requires_both_orders_and_acknowledgements(self):
        self.command(self.alice, 'cpu_match', stadium=1)
        # Replace the CPU participant before any commands to exercise both sides.
        with self.service.store.transaction():
            match=self.service.store.active_match(self.identity(self.alice)); match['profiles'][1]=self.identity(self.bob)
            self.service.store.db.execute('UPDATE participants SET profile_id=? WHERE match_id=? AND side=2',(self.identity(self.bob),match['id']))
            self.service.store.save_match(match)
            self.service.finish_placement(match); self.service.store.save_match(match)
        for turn in (1,2):
            self.protocol(self.alice,'ORDERS',{'turn':turn,'orders':[]})
            self.assertEqual(self.service.store.match(match['id'])['phase'],'orders')
            self.protocol(self.bob,'ORDERS',{'turn':turn,'orders':[]})
            self.protocol(self.alice,'RESOLUTION_DONE',{'turn':turn})
            self.assertEqual(self.service.store.match(match['id'])['phase'],'resolution')
            self.protocol(self.bob,'RESOLUTION_DONE',{'turn':turn})
        self.assertEqual(self.service.store.match(match['id'])['phase'],'ended')
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM match_results').fetchone()[0],2)

    def test_empty_placement_submission_uses_default_zones(self):
        self.command(self.alice, "cpu_match", stadium=1)
        match=self.service.store.active_match(self.identity(self.alice))
        self.protocol(self.alice,'PLACEMENT',{'turn':1,'boufbowlerPositions':[]})
        match=self.service.store.match(match['id'])
        self.assertEqual(match['phase'],'orders')
        positions={tuple(e['position'].values()) for e in match['world']['entities'] if e['team_id']==0}
        defaults={tuple(z['defaultCell'].values()) for z in self.service.match_information(match,1)['placementZone']}
        self.assertEqual(positions,defaults)

    def test_chat_advertises_language_keys_and_preserves_french_messages(self):
        events=self.service.store.poll(self.identity(self.alice),0)
        event=next(e for e in events if e['type']=='CHANNEL_AVAILABLE_NOTIFICATION')
        options=self.service.chat_codec.open_envelope(bytes.fromhex(event['hex']))['payload']['options']
        languages={o.get('lang') for o in options if o['channelType']==2}
        self.assertEqual(languages,{'fr','en','de','es'})
        self.assertTrue(all(o['rateLimit']==1 for o in options))
        for player in (self.alice,self.bob):
            self.service.community({'session':player['session'],'action':'channels','languages':['fr']})
        data={'toChannel':{'channelType':2,'lang':'fr'},'message':'Bonjour'}
        self.command(self.alice,'chat',hex=self.service.chat_codec.envelope('SEND_MESSAGE_TO_CHANNEL_REQUEST',data).hex())
        event=next(e for e in self.service.store.poll(self.identity(self.bob),0) if e['type']=='RECEIVE_FROM_CHANNEL')
        message=self.service.chat_codec.open_envelope(bytes.fromhex(event['hex']))['payload']
        self.assertEqual(message['fromChannel'],{'channelType':2,'lang':'fr'})
        self.assertEqual(message['message'],'Bonjour')

    def test_chat_private_messages_do_not_reach_other_profiles(self):
        charlie=self.service.hello({'nickname':'Charlie','clubs':[initial_club()]})
        before=self.service.store.db.execute('SELECT MAX(seq) FROM events').fetchone()[0]
        hex=self.service.chat_codec.envelope('SEND_MESSAGE_TO_CLIENT_REQUEST',{'toNickname':'Bob','message':'Hello Bob'}).hex()
        self.command(self.alice,'chat',hex=hex)
        bob=self.service.store.poll(self.identity(self.bob),before)
        self.assertEqual(bob[0]['type'],'RECEIVE_FROM_CLIENT')
        self.assertEqual(self.service.chat_codec.open_envelope(bytes.fromhex(bob[0]['hex']))['payload']['message'],'Hello Bob')
        self.assertEqual(self.service.store.poll(self.identity(charlie),before),[])
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM chat_messages').fetchone()[0],1)

    def test_configured_tournament_records_results_and_emits_leaderboard(self):
        self.protocol(self.alice,'MATCH_REQUEST',{'tournamentId':'1'})
        self.protocol(self.bob,'MATCH_REQUEST',{'tournamentId':'1'})
        with self.service.store.transaction():
            match=self.service.store.active_match(self.identity(self.alice)); match['score']=[1,0]
            self.service.end_match(match)
        self.protocol(self.alice,'OUTSTANDING_TOURNAMENTS_REQUEST',{})
        self.protocol(self.alice,'TOURNAMENT_LEADERBOARD_REQUEST',{'tournamentId':'1'})
        self.protocol(self.alice,'RUNNING_TOURNAMENT_MATCHES_REQUEST',{})
        entries=self.service.tournament_entries(self.config['general']['tournament'])
        self.assertEqual(entries[0][1]['tournamentPoints'],3)
        self.protocol(self.alice,'LADDER_BY_NICK_REQUEST',{'self':True})

    def test_replay_export_verifies_and_rejects_unrelated_profiles(self):
        from backend.replay import export_replay
        self.start(); self.protocol(self.alice,'ORDERS',{'turn':1,'orders':[]})
        match=self.service.store.active_match(self.identity(self.alice))
        replay=export_replay(self.service,match['id'],True,self.identity(self.alice))
        self.assertTrue(replay['verified'])
        self.assertFalse(replay['completed'])
        self.assertEqual(replay['records'][0]['result']['turn_number'],1)
        with self.assertRaisesRegex(ServiceError,'participant'):
            export_replay(self.service,match['id'],False,self.identity(self.bob))


    def test_regeneration_uses_class_rate_without_changing_recorded_resolution(self):
        self.start()
        with self.service.store.transaction():
            match=self.service.store.active_match(self.identity(self.alice))
            match['world']['entities'][0]['hp']=5
            match['orders']['2']={'player_id':'cpu','turn_number':1,'team_index':1,'nonce':'wait','actions':[]}
            self.service.store.save_match(match)
        self.protocol(self.alice,'ORDERS',{'turn':1,'orders':[]})
        self.protocol(self.alice,'RESOLUTION_DONE',{'turn':1})
        restored=self.service.store.match(match['id'])
        self.assertEqual(restored['world']['entities'][0]['hp'],8)
        record=json.loads(self.service.store.db.execute('SELECT record_json FROM turns WHERE match_id=?',(match['id'],)).fetchone()[0])
        self.assertEqual(record['result']['final_world_state']['entities'][0]['hp'],5)

    def test_spectators_receive_scenarios_but_cannot_advance_matches(self):
        self.start()
        self.protocol(self.bob,'MATCH_SPECTATE_REQUEST',{'playerNickname':'Alice'})
        self.protocol(self.alice,'ORDERS',{'turn':1,'orders':[]})
        match=self.service.store.active_match(self.identity(self.alice))
        self.protocol(self.bob,'RESOLUTION_DONE',{'turn':1})
        self.assertEqual(self.service.store.match(match['id'])['acks'],[])
        events=self.service.store.poll(self.identity(self.bob),0)
        self.assertIn('RESOLUTION_SCENARIO',[event['type'] for event in events])
        self.protocol(self.bob,'STOP_SPECTATING',{})
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM spectators').fetchone()[0],0)


    def test_simulation_worker_restarts_after_unexpected_exit(self):
        self.start()
        self.service.engine.process.kill();self.service.engine.process.wait()
        self.protocol(self.alice,'ORDERS',{'turn':1,'orders':[]})
        match=self.service.store.active_match(self.identity(self.alice))
        self.assertEqual(match['phase'],'resolution')
        self.assertIsNone(self.service.engine.process.poll())


if __name__ == "__main__":
    unittest.main()
