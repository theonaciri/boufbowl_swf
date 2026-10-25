"""Privacy boundaries: session ownership, password confirmation, shared result retention."""
from copy import deepcopy
from functools import partial
from http.server import ThreadingHTTPServer
import json
from threading import Thread
import unittest
from urllib.request import Request, urlopen
from unittest.mock import patch

from backend.server import Handler
from backend.storage import ServiceError
from tests import test_accounts_matchmaking as helpers


class AccountPrivacyTests(unittest.TestCase):
    setUp = helpers.AccountMatchmakingTests.setUp
    tearDown = helpers.AccountMatchmakingTests.tearDown
    pid = helpers.AccountMatchmakingTests.pid
    command = helpers.AccountMatchmakingTests.command
    register = helpers.AccountMatchmakingTests.register
    protocol = helpers.AccountMatchmakingTests.protocol

    def privacy(self, player, action='export', **fields):
        return self.s.account({'session': player['session'], 'action': action, **fields})

    def delete(self, player, nickname='Alice', **fields):
        return self.privacy(player, 'delete', nickname=nickname, confirmation='SUPPRIMER', **fields)

    def assert_code(self, code, callback):
        with self.assertRaises(ServiceError) as raised:
            callback()
        self.assertEqual(raised.exception.code, code)

    def test_ownership_and_password_required_even_for_linked_device_session(self):
        account = self.register(self.a)
        self.assert_code('ACCOUNT_AUTH', lambda: self.privacy(self.a))
        self.assert_code('ACCOUNT_AUTH', lambda: self.delete(self.a))
        # Supplying another profile or username cannot redirect an authenticated operation.
        data = self.privacy(self.b, profile_id=self.pid(account), username='alice-account')['export']
        self.assertEqual(data['identity']['nickname'], 'Bob')
        self.assertNotIn('alice-account', json.dumps(data))
        self.assert_code('ACCOUNT_CONFIRMATION', lambda: self.delete(account, nickname='Bob', password='test-password-123'))
        self.assertEqual(self.pid(self.a), self.pid(account))
        result = self.delete(self.a, password='test-password-123', device_session=self.a['session'], account_session=account['session'])
        self.assertTrue(result['clear_device_session'])
        self.assertTrue(result['clear_account_session'])
        for player in (self.a, account):
            self.assert_code('SESSION_DELETED', lambda: self.s.hello({'session': player['session']}))
        self.assert_code('ACCOUNT_AUTH', lambda: self.s.account({'action':'login','username':'alice-account','password':'test-password-123'}))

    def test_password_failures_persist_and_rate_limit_privacy_actions(self):
        account = self.register(self.a)
        for _ in range(5):
            self.assert_code('ACCOUNT_AUTH', lambda: self.privacy(account, password='bad-password-123'))
        self.assert_code('ACCOUNT_RATE_LIMIT', lambda: self.delete(account, password='test-password-123'))
        self.s.store.db.execute('UPDATE auth_attempts SET reset_at=0')
        self.assertTrue(self.privacy(account, password='test-password-123')['ok'])

    def test_device_confirmation_is_explicit_and_preserves_unrelated_local_sessions(self):
        self.assert_code('ACCOUNT_CONFIRMATION', lambda: self.privacy(self.a, 'delete'))
        old = self.pid(self.a)
        result = self.delete(self.a, device_session=self.a['session'], account_session=self.b['session'])
        self.assertTrue(result['clear_device_session'])
        self.assertFalse(result['clear_account_session'])
        self.assertIsNone(self.s.store.db.execute('SELECT 1 FROM profiles WHERE id=?', (old,)).fetchone())
        self.assert_code('SESSION_DELETED', lambda: self.s.hello({'session': self.a['session'], 'nickname':'Alice', 'clubs':[]}))
        self.assertEqual(self.s.hello({'session':self.b['session']})['profile']['nickname'], 'Bob')
        from backend.service import Service
        self.s.close()
        self.s = Service(self.path, self.config)
        self.assert_code('SESSION_DELETED', lambda: self.s.hello({'session': self.a['session']}))
        self.assertEqual(self.s.hello({'session':self.b['session']})['profile']['nickname'], 'Bob')

    def test_active_match_blocks_deletion_without_mutating_game_or_sessions(self):
        with self.s.store.transaction():
            match = self.s.create_match(self.pid(self.a), self.pid(self.b), 1)
        before = deepcopy(self.s.store.match(match['id']))
        self.assert_code('ACCOUNT_MATCH_ACTIVE', lambda: self.delete(self.a))
        self.assertEqual(self.s.store.match(match['id']), before)
        self.assertEqual(self.pid(self.a), before['profiles'][0])
        # Export remains available during a game but never includes simulation inputs.
        data = self.privacy(self.a)['export']
        self.assertEqual(data['match_results'], [])
        self.assertNotIn('orders', data)

    def test_export_is_allowlisted_and_contains_no_opponent_private_data_or_auth_secrets(self):
        account = self.register(self.a)
        bob = self.register(self.b, 'bob-private-account')
        alice_id, bob_id = self.pid(self.a), self.pid(self.b)
        with self.s.store.transaction():
            self.s.store.db.execute('INSERT INTO chat_messages(sender,recipient,message,created) VALUES(?,?,?,1)', (bob_id, alice_id, 'opponent-private-message'))
            self.s.store.db.execute('INSERT INTO chat_messages(sender,recipient,message,created) VALUES(?,?,?,2)', (alice_id, bob_id, 'my-own-message'))
            match = self.s.create_match(alice_id, bob_id, 1)
            match.update(seed=123456789, turn_seeds={'1':987654321}, orders={'2':{'secret':'opponent-order'}})
            self.s.store.save_match(match)
        data = self.privacy(account, password='test-password-123')['export']
        serialized = json.dumps(data)
        for secret in (account['session'], account['recovery_code'], bob['session'], bob['recovery_code'],
                       'bob-private-account', 'opponent-private-message', 'opponent-order', '123456789', '987654321'):
            self.assertNotIn(secret, serialized)
        def walk(value):
            if isinstance(value, dict):
                self.assertFalse(set(value) & {'password_hash','salt','token_hash','recovery_hash','session','seed','turn_seeds','orders','records','hex'})
                for child in value.values(): walk(child)
            elif isinstance(value, list):
                for child in value: walk(child)
        walk(data)
        self.assertEqual(data['sent_messages'][0]['message'], 'my-own-message')
        self.assertGreaterEqual(sum(row['requests'] for row in data['activity']), 1)

    def test_deletion_scrubs_snapshots_caches_social_activity_and_retains_others_results(self):
        alice_id, bob_id = self.pid(self.a), self.pid(self.b)
        self.s.community({'session':self.a['session'],'action':'friend','verb':'add','nickname':'Bob'})
        with self.s.store.transaction():
            match = self.s.create_match(alice_id, bob_id, 1, tournament=1, source='tournament')
            match['score'] = [2, 1]
            self.s.end_match(match)
            self.s.store.save_match(match)
            # Exercise frozen standings and cached encoded packets as well as live tables.
            self.s.store.db.execute('UPDATE tournaments SET final_entries_json=? WHERE id=1',
                (json.dumps([[alice_id, {'player':self.s.player_summary(alice_id),'currentRank':1,'tournamentPoints':3}], [bob_id, {'player':self.s.player_summary(bob_id),'currentRank':2,'tournamentPoints':0}]]),))
            self.s.emit_chat(bob_id, 'RECEIVE_FROM_CLIENT', {'fromNickname':'Alice','message':'erase-my-chat'})
            self.s.store.db.execute('INSERT INTO chat_messages(sender,recipient,message,created) VALUES(?,?,?,1)', (alice_id,bob_id,'erase-my-chat'))
            self.s.store.db.execute('INSERT INTO blocks VALUES(?,?,1)', (bob_id,alice_id))
            self.s.store.db.execute('INSERT INTO reports(reporter,target,reason,created) VALUES(?,?,?,1)', (bob_id,alice_id,'report'))
        with self.s.store.transaction():
            active_other = self.s.create_match(bob_id, None, 1)
            self.s.store.db.execute('INSERT INTO turns VALUES(?,?,?)', (match['id'], 1, json.dumps({'nickname':'Alice','profile_id':alice_id,'mechanics':{'score':[2,1]}})))
        before = self.s.store.profile(bob_id)
        self.s.tracking.flush(force=True)
        self.s.tracking.activity(alice_id, {'client_id':'pending-client'})
        self.delete(self.a)
        self.s.tracking.flush(force=True)
        db = self.s.store.db
        self.assertEqual(self.s.store.profile(bob_id), before)
        retained = self.s.store.match(match['id'])
        self.assertEqual(retained['score'], [2,1])
        self.assertEqual(self.s.store.match(active_other['id']), active_other)
        turn = db.execute('SELECT record_json FROM turns WHERE match_id=?', (match['id'],)).fetchone()[0]
        self.assertNotIn('Alice', turn)
        self.assertNotIn(alice_id, turn)
        self.assertEqual(json.loads(turn)['mechanics']['score'], [2,1])
        self.assertEqual(retained['profiles'][1], bob_id)
        self.assertNotEqual(retained['profiles'][0], alice_id)
        self.assertNotIn('Alice', json.dumps(retained))
        self.assertNotIn(alice_id, json.dumps(retained))
        self.assertEqual(db.execute('SELECT outcome FROM match_results WHERE profile_id=?', (bob_id,)).fetchone()[0], 'defeats')
        for table in ('sessions','accounts','presence','events','commands','chat_subscriptions','replay_access','spectators',
                      'tournament_watchers','tournament_intentions','tracking_activity','tracking_clients','tracking_visits','tracking_receipts'):
            self.assertEqual(db.execute(f'SELECT COUNT(*) FROM {table} WHERE profile_id=?', (alice_id,)).fetchone()[0], 0, table)
        for table in ('friendships','blocks','reports','chat_messages'):
            self.assertEqual(db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0], 0, table)
        standings = json.loads(db.execute('SELECT final_entries_json FROM tournaments WHERE id=1').fetchone()[0])
        self.assertNotIn(alice_id, json.dumps(standings))
        self.assertEqual(standings[1][1]['player']['nickname'], 'Bob')
        for row in db.execute('SELECT packet_json FROM events WHERE profile_id=?', (bob_id,)):
            packet = json.loads(row[0])
            if 'hex' in packet:
                codec = self.s.chat_codec if packet['channel']=='CHAT' else self.s.codec
                decoded = json.dumps(codec.open_envelope(bytes.fromhex(packet['hex'])))
                self.assertNotIn('Alice', decoded)
                self.assertNotIn('erase-my-chat', decoded)
        self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
        history = self.s.community({'session':self.b['session'],'action':'history'})
        self.assertNotIn('Alice', json.dumps(history))

    def test_all_foreign_key_dependents_are_removed_or_rekeyed(self):
        alice, bob = self.pid(self.a), self.pid(self.b)
        db = self.s.store.db
        with self.s.store.transaction():
            db.execute('INSERT INTO tournament_participants VALUES(1,?,1)', (alice,))
            db.execute('INSERT INTO tournament_watchers VALUES(?)', (alice,))
            db.execute('INSERT INTO tournament_intentions VALUES(1,?,1)', (alice,))
            db.execute("INSERT INTO tournament_rewards VALUES(1,?,1,'{}',1)", (alice,))
            db.execute("INSERT INTO cosmetic_unlocks VALUES(?,'test',1)", (alice,))
            db.execute("INSERT INTO economy_ledger(profile_id,item_id,amount_json,created) VALUES(?,'test','{}',1)", (alice,))
            season = 987
            db.execute("INSERT INTO seasons(id,settings_json) VALUES(?,'{}')", (season,))
            db.execute("INSERT OR REPLACE INTO season_rankings VALUES(?,?,'{\"wins\":1,\"tournament_wallet\":{}}')", (season, alice))
            db.execute("INSERT INTO profile_roles VALUES(?,'moderator')", (alice,))
            db.execute("INSERT INTO sanctions VALUES(?,'mute',NULL,'old personal reason',?)", (bob,alice))
            db.execute("INSERT INTO moderation_audit(actor,target,action,reason,created) VALUES(?,?,'mute','old personal reason',1)", (alice,bob))
            db.execute("INSERT INTO admin_events(actor,action,details,created) VALUES(?,'setting','old personal details',1)", (alice,))
            db.execute("INSERT INTO tournament_rounds VALUES(1,99,'finished',?)", (json.dumps({'eligible':[alice,bob],'eliminated':{alice:1},'pairs':[[alice,bob]]}),))
        self.delete(self.a)
        self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
        for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
            for record in db.execute('SELECT * FROM "' + row['name'] + '"'):
                self.assertNotIn(alice, json.dumps(tuple(record)), row['name'])
        sanction = db.execute('SELECT * FROM sanctions WHERE profile_id=?', (bob,)).fetchone()
        self.assertEqual(sanction['kind'], 'mute')
        self.assertIsNone(sanction['actor'])
        self.assertNotIn('old personal', json.dumps([tuple(r) for r in db.execute('SELECT * FROM admin_events')]))

    def test_recorded_replay_still_verifies_after_deletion(self):
        from backend.replay import export_replay
        with self.s.store.transaction():
            match = self.s.create_match(self.pid(self.a), self.pid(self.b), 1)
            self.s.finish_placement(match)
            self.s.store.save_match(match)
        self.protocol(self.a, 'ORDERS', {'turn':1,'orders':[]})
        self.protocol(self.b, 'ORDERS', {'turn':1,'orders':[]})
        with self.s.store.transaction():
            match = self.s.store.match(match['id'])
            self.s.end_match(match)
        original_id = self.pid(self.a)
        before = export_replay(self.s, match['id'], True, self.pid(self.b))
        self.delete(self.a)
        after = export_replay(self.s, match['id'], True, self.pid(self.b))
        self.assertTrue(after['verified'])
        self.assertEqual([r['result'] for r in before['records']], [r['result'] for r in after['records']])
        self.assertNotIn(original_id, json.dumps(after))
        self.assertNotIn('Alice', json.dumps(after))

    def test_failure_rolls_back_all_sql_changes(self):
        identity = self.pid(self.a)
        before = self.s.store.profile(identity)
        with patch.object(self.s, 'stop_spectating', side_effect=RuntimeError('injected')):
            with self.assertRaisesRegex(RuntimeError, 'injected'):
                self.delete(self.a)
        self.assertEqual(self.s.store.profile(identity), before)
        self.assertEqual(self.s.store.db.execute('SELECT COUNT(*) FROM profiles').fetchone()[0], 2)
        self.assertEqual(self.pid(self.a), identity)

    def test_existing_http_account_route_exports_deletes_and_revokes(self):
        class QuietHandler(Handler):
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1',0), partial(QuietHandler, directory=self.temp.name))
        server.service = self.s
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def request(body):
            req = Request(f'http://127.0.0.1:{server.server_port}/api/account', data=json.dumps(body).encode(), headers={'Content-Type':'application/json'})
            with urlopen(req, timeout=5) as response:
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                return json.load(response)
        try:
            self.assertEqual(request({'action':'export','session':self.a['session']})['export']['identity']['nickname'], 'Alice')
            self.assertFalse(request({'action':'delete','session':self.a['session']})['ok'])
            self.assertTrue(request({'action':'delete','session':self.a['session'],'nickname':'Alice','confirmation':'SUPPRIMER'})['deleted'])
            self.assertEqual(request({'action':'export','session':self.a['session']})['code'], 'SESSION_DELETED')
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)
