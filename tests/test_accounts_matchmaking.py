from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

from backend.service import Service
from backend.storage import ServiceError
from tests.test_backend import initial_club
from tools.game_config import load_config


class AccountMatchmakingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'state.sqlite'
        self.config=load_config();self.config['rules']['match'].update(turns_per_match=2,turns_per_period=2)
        self.s=Service(self.path,self.config);self.n=0
        self.a=self.s.hello({'nickname':'Alice','clubs':[initial_club()]})
        self.b=self.s.hello({'nickname':'Bob','clubs':[initial_club()]})

    def tearDown(self):
        self.s.close();self.temp.cleanup()

    def pid(self, player):return self.s.store.authenticate(player['session'])

    def command(self, player, operation='queue_join', **fields):
        self.n+=1
        return self.s.command({'session':player['session'],'request_id':str(self.n),'operation':operation,**fields})

    def protocol(self,player,name,payload):
        return self.command(player,'protocol',hex=self.s.codec.envelope(name,payload).hex())

    def register(self, player, username='alice-account'):
        return self.s.account({'action':'register','username':username,'password':'test-password-123','session':player['session']})

    def test_link_device_preserves_profile_clubs_stats_and_device_option(self):
        before=self.s.store.profile(self.pid(self.a))
        registered=self.register(self.a)
        self.assertEqual(self.pid(registered),self.pid(self.a))
        self.assertEqual(self.s.store.profile(self.pid(registered)),before)
        self.assertEqual(self.s.hello({'session':self.a['session']})['auth_mode'],'device')
        self.assertEqual(registered['auth_mode'],'account')
        self.assertEqual(registered['profile']['account_username'],'alice-account')
        row=self.s.store.db.execute('SELECT * FROM accounts').fetchone()
        self.assertNotEqual(row['password_hash'],'test-password-123')
        self.assertNotEqual(row['recovery_hash'],registered['recovery_code'])

    def test_login_other_device_case_insensitive_and_survives_restart(self):
        registered=self.register(self.a)
        self.s.close();self.s=Service(self.path,self.config)
        logged=self.s.account({'action':'login','username':'ALICE-ACCOUNT','password':'test-password-123'})
        self.assertEqual(self.pid(logged),self.pid(registered))
        self.assertNotEqual(logged['session'],registered['session'])

    def test_password_change_revokes_every_old_session(self):
        registered=self.register(self.a)
        logged=self.s.account({'action':'login','username':'alice-account','password':'test-password-123'})
        changed=self.s.account({'action':'password','username':'alice-account','password':'test-password-123',
                               'new_password':'replacement-password','session':logged['session']})
        for old in (self.a,registered,logged):
            with self.assertRaises(ServiceError):self.pid(old)
        self.assertEqual(changed['auth_mode'],'account')
        with self.assertRaises(ServiceError):self.s.account({'action':'login','username':'alice-account','password':'test-password-123'})
        self.assertEqual(self.pid(changed),self.pid(self.s.account({'action':'login','username':'alice-account','password':'replacement-password'})))

    def test_recovery_is_one_time_and_revokes_old_tokens(self):
        registered=self.register(self.a)
        recovered=self.s.account({'action':'recover','username':'alice-account','recovery_code':registered['recovery_code'],
                                  'new_password':'recovery-password-123'})
        self.assertNotEqual(recovered['recovery_code'],registered['recovery_code'])
        with self.assertRaises(ServiceError):self.pid(registered)
        with self.assertRaises(ServiceError):self.s.account({'action':'recover','username':'alice-account',
            'recovery_code':registered['recovery_code'],'new_password':'another-password-123'})
        logged=self.s.account({'action':'login','username':'alice-account','password':'recovery-password-123'})
        self.assertEqual(self.pid(recovered),self.pid(logged))

    def test_login_failures_are_persisted_and_throttled(self):
        self.register(self.a)
        body={'action':'login','username':'alice-account','password':'wrong-password-123'}
        for _ in range(5):
            with self.assertRaisesRegex(ServiceError,'Invalid'):self.s.account(body,'peer-1')
        self.s.close();self.s=Service(self.path,self.config)
        with self.assertRaisesRegex(ServiceError,'five minutes'):self.s.account(body,'peer-1')
        self.s.account({'action':'login','username':'alice-account','password':'test-password-123'},'peer-2')

    def test_account_username_cannot_be_claimed_by_another_device(self):
        self.register(self.a)
        with self.assertRaises(ServiceError):self.register(self.b)
        self.assertEqual(self.s.store.db.execute('SELECT COUNT(*) FROM accounts').fetchone()[0],1)

    def test_logout_revokes_only_that_token_and_cancels_search(self):
        registered=self.register(self.a)
        self.command(registered)
        self.s.account({'action':'logout','session':registered['session']})
        with self.assertRaises(ServiceError):self.pid(registered)
        self.assertEqual(self.s.matchmaking_status(self.pid(self.a))['status'],'idle')

    def test_two_accounts_or_devices_match_and_finish_as_humans(self):
        self.a=self.register(self.a);self.b=self.register(self.b,'bob-account')
        self.assertEqual(self.command(self.a)['matchmaking']['status'],'waiting')
        self.assertIsNone(self.s.store.active_match(self.pid(self.a)))
        self.command(self.b)
        match=self.s.store.active_match(self.pid(self.a))
        self.assertEqual(match['profiles'],[self.pid(self.a),self.pid(self.b)])
        for player in (self.a,self.b):self.protocol(player,'PLACEMENT',{'turn':1,'boufbowlerPositions':[]})
        for turn in (1,2):
            self.protocol(self.a,'ORDERS',{'turn':turn,'orders':[]})
            self.protocol(self.a,'ORDERS',{'turn':turn,'orders':[]})
            self.assertEqual(self.s.store.match(match['id'])['phase'],'orders')
            self.protocol(self.b,'ORDERS',{'turn':turn,'orders':[]})
            self.protocol(self.a,'RESOLUTION_DONE',{'turn':turn})
            self.assertEqual(self.s.store.match(match['id'])['phase'],'resolution')
            self.protocol(self.b,'RESOLUTION_DONE',{'turn':turn})
        self.assertEqual(self.s.store.match(match['id'])['phase'],'ended')
        self.assertEqual(self.s.store.db.execute('SELECT COUNT(*) FROM match_results').fetchone()[0],2)
        for player in (self.a,self.b):
            self.assertIn('MATCH_END',[e['type'] for e in self.s.store.poll(self.pid(player),0)])

    def test_normal_match_request_searches_and_cancel_removes_queue(self):
        self.protocol(self.a,'MATCH_REQUEST',{})
        self.assertEqual(self.s.matchmaking_status(self.pid(self.a))['status'],'waiting')
        self.protocol(self.a,'CANCEL_MATCH_REQUEST',{})
        self.assertEqual(self.s.matchmaking_status(self.pid(self.a))['status'],'idle')
        self.command(self.b)
        self.assertIsNone(self.s.store.active_match(self.pid(self.b)))

    def test_stadium_intersection_and_rating_window(self):
        self.command(self.a,stadiums=[1]);self.command(self.b,stadiums=[2])
        self.assertIsNone(self.s.store.active_match(self.pid(self.a)))
        self.command(self.b,stadiums=[1,2])
        self.assertEqual(self.s.store.active_match(self.pid(self.a))['stadium'],1)

    def test_rating_search_widens(self):
        with self.s.store.transaction():
            stats=self.s.store.profile(self.pid(self.b))['statistics'];stats['rating']=1600
            self.s.store.db.execute('UPDATE profiles SET statistics_json=? WHERE id=?',(json.dumps(stats),self.pid(self.b)))
        self.command(self.a);self.command(self.b)
        self.assertIsNone(self.s.store.active_match(self.pid(self.a)))
        with self.s.store.transaction():
            self.s.store.db.execute('UPDATE matchmaking_queue SET joined=joined-100')
            self.s.match_queued_players()
        self.assertIsNotNone(self.s.store.active_match(self.pid(self.a)))

    def test_same_profile_on_two_devices_cannot_match_itself(self):
        other=self.s.hello({'session':self.a['session']})
        self.command(self.a);self.command(other)
        self.assertEqual(self.s.store.db.execute('SELECT COUNT(*) FROM matchmaking_queue').fetchone()[0],1)
        self.assertIsNone(self.s.store.active_match(self.pid(self.a)))

    def test_disconnected_queue_expires_without_poll_reviving_it(self):
        self.command(self.a)
        with self.s.store.transaction():self.s.store.db.execute('UPDATE matchmaking_queue SET heartbeat=heartbeat-100')
        status=self.s.poll({'session':self.a['session'],'cursor':0})['matchmaking']
        self.assertEqual(status['status'],'idle')

    def test_queue_persists_across_server_restart(self):
        self.command(self.a)
        self.s.close();self.s=Service(self.path,self.config)
        self.assertEqual(self.s.hello({'session':self.a['session']})['matchmaking']['status'],'waiting')
        self.command(self.b)
        self.assertIsNotNone(self.s.store.active_match(self.pid(self.a)))

    def test_parallel_joins_assign_each_profile_once(self):
        players=[self.a,self.b]+[self.s.hello({'nickname':f'Player{i}','clubs':[initial_club()]}) for i in range(6)]
        def join(player):return self.s.command({'session':player['session'],'request_id':'join','operation':'queue_join'})
        with ThreadPoolExecutor(8) as pool:list(pool.map(join,players))
        rows=self.s.store.db.execute('SELECT profile_id FROM participants').fetchall()
        self.assertEqual(len(rows),8);self.assertEqual(len({r[0] for r in rows}),8)
        self.assertTrue(all(r[0] is not None for r in rows))

    def test_pending_challenge_reappears_after_guest_login(self):
        self.command(self.a,'challenge',nickname='Bob',stadium=2)
        restored=self.s.hello({'session':self.b['session']})
        events=self.s.poll({'session':self.b['session'],'cursor':restored['cursor']})['events']
        self.assertIn('CHALLENGE_PROPOSAL',[e['type'] for e in events])
        offer=self.s.store.db.execute('SELECT id FROM challenges').fetchone()[0]
        self.protocol(self.b,'CHALLENGE_ANSWER',{'offerId':offer,'answer':2})
        self.assertEqual(self.s.store.active_match(self.pid(self.a))['stadium'],2)

    def test_switching_between_queue_and_challenge_cancels_old_search(self):
        self.command(self.a)
        self.command(self.a,'challenge',nickname='Bob',stadium=1)
        self.assertEqual(self.s.matchmaking_status(self.pid(self.a))['status'],'idle')
        self.command(self.a)
        self.assertEqual(self.s.store.db.execute('SELECT status FROM challenges').fetchone()[0],'cancelled')

    def test_chat_defaults_to_general_and_room_follows_match_lifecycle(self):
        initial=self.s.store.poll(self.pid(self.a),0)
        packet=next(e for e in initial if e['type']=='CHANNEL_AVAILABLE_NOTIFICATION')
        options=self.s.chat_codec.open_envelope(bytes.fromhex(packet['hex']))['payload']['options']
        self.assertNotIn(3,[o['channelType'] for o in options])
        self.command(self.a);self.command(self.b)
        packets=[e for e in self.s.store.poll(self.pid(self.a),0) if e['type']=='CHANNEL_AVAILABLE_NOTIFICATION']
        options=self.s.chat_codec.open_envelope(bytes.fromhex(packets[-1]['hex']))['payload']['options']
        self.assertIn(3,[o['channelType'] for o in options])
        self.protocol(self.a,'SURRENDER',{})
        event=next(e for e in self.s.store.poll(self.pid(self.a),0) if e['type']=='CHANNEL_UNAVAILABLE_NOTIFICATION')
        self.assertEqual(self.s.chat_codec.open_envelope(bytes.fromhex(event['hex']))['payload']['channels'],[{'channelType':3}])

    def test_account_api_over_tls(self):
        import shutil, ssl, subprocess, threading
        from functools import partial
        from http.server import ThreadingHTTPServer
        from urllib.request import Request, urlopen
        from backend.server import Handler
        from tools.game_config import ROOT
        if not shutil.which('openssl'): self.skipTest('OpenSSL certificate generator unavailable')
        cert=Path(self.temp.name)/'cert.pem';key=Path(self.temp.name)/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),
            '-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=IP:127.0.0.1'],
            check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        class QuietHandler(Handler):
            def log_message(self,*args): pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
        server.service=self.s;context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert,key)
        server.socket=context.wrap_socket(server.socket,server_side=True)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            body={'action':'register','username':'tls-account','password':'tls-password-123','session':self.a['session']}
            request=Request(f'https://127.0.0.1:{server.server_port}/api/account',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
            with urlopen(request,context=ssl.create_default_context(cafile=str(cert)),timeout=10) as response:
                account=json.load(response)
            self.assertEqual(account['auth_mode'],'account')
            self.assertEqual(self.pid(account),self.pid(self.a))
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)

    def test_v1_database_migration_preserves_device_token(self):
        path=Path(self.temp.name)/'old.sqlite';club=initial_club()
        collection={'active':'1','clubs':{'1':club}};token='old-device-token-long-enough'
        c=sqlite3.connect(path)
        c.executescript('CREATE TABLE schema_versions(version INTEGER PRIMARY KEY);INSERT INTO schema_versions VALUES(1);'
            'CREATE TABLE profiles(id TEXT PRIMARY KEY,nickname TEXT NOT NULL COLLATE NOCASE UNIQUE,club_json TEXT NOT NULL,statistics_json TEXT NOT NULL,created REAL NOT NULL);'
            'CREATE TABLE sessions(token_hash TEXT PRIMARY KEY,profile_id TEXT NOT NULL REFERENCES profiles(id),expires REAL NOT NULL);')
        c.execute('INSERT INTO profiles VALUES(?,?,?,?,?)',('legacy','Legacy',json.dumps(collection),json.dumps({'wins':0,'draws':0,'defeats':0,'rating':1000}),time.time()))
        c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),'legacy',time.time()+1000));c.commit();c.close()
        other=Service(path,self.config)
        try:
            self.assertEqual(other.hello({'session':token})['auth_mode'],'device')
            self.assertEqual(other.store.authenticate(token),'legacy')
        finally:other.close()

    def test_tournament_queue_is_human_and_separate_from_normal_search(self):
        self.command(self.a,'tournament_match',tournament_id=1)
        self.assertIsNone(self.s.store.active_match(self.pid(self.a)))
        self.command(self.b)
        self.assertIsNone(self.s.store.active_match(self.pid(self.b)))
        self.command(self.b,'tournament_match',tournament_id=1)
        match=self.s.store.active_match(self.pid(self.a))
        self.assertEqual(set(match['profiles']),{self.pid(self.a),self.pid(self.b)})
        self.assertEqual(match['tournament'],1)
        self.assertEqual(match['stadium'],self.config['general']['tournament']['stadium'])

    def test_tournament_pairing_never_reuses_a_busy_opponent(self):
        c=self.s.hello({'nickname':'Charlie','clubs':[initial_club()]})
        d=self.s.hello({'nickname':'Diane','clubs':[initial_club()]})
        for player in (self.a,self.b,c,d):
            self.command(player,'tournament_match',tournament_id=1)
        matches=[json.loads(row[0]) for row in self.s.store.db.execute('SELECT state_json FROM matches')]
        self.assertEqual(len(matches),2)
        participants=[p for match in matches for p in match['profiles']]
        self.assertEqual(len(set(participants)),4)
        with self.assertRaises(ServiceError):self.command(self.a,'tournament_match',tournament_id=1)
        self.assertEqual(self.s.store.db.execute('SELECT COUNT(*) FROM matches').fetchone()[0],2)

    def test_tournament_search_restores_and_expires_without_cpu_fallback(self):
        self.command(self.a,'tournament_match',tournament_id=1)
        self.s.close();self.s=Service(self.path,self.config)
        self.assertEqual(self.s.matchmaking_status(self.pid(self.a))['tournament'],'1')
        with self.s.store.transaction():
            self.s.store.db.execute('UPDATE matchmaking_queue SET joined=joined-1000')
            self.s.match_queued_players()
        self.assertEqual(self.s.matchmaking_status(self.pid(self.a))['status'],'idle')
        self.assertEqual(self.s.store.db.execute('SELECT COUNT(*) FROM matches').fetchone()[0],0)

    def test_closed_tournament_removes_waiting_players(self):
        self.command(self.a,'tournament_match',tournament_id=1)
        self.s.config['general']['tournament']['end_time']=time.time()-1
        with self.s.store.transaction():self.s.match_queued_players()
        self.assertEqual(self.s.matchmaking_status(self.pid(self.a))['status'],'idle')
        with self.assertRaises(ServiceError):self.command(self.b,'tournament_match',tournament_id=1)

    def test_match_request_uses_explicit_owned_team_and_preserves_roster(self):
        selected=deepcopy(initial_club());selected['clubId']='2';selected['clubName']='Selected second team'
        selected['boufbowler'][0]['boufbowlerClass']=14
        with self.s.store.transaction():
            collection=self.s.collection(self.pid(self.a));collection['clubs']['2']=selected
            self.s.store.save_club(self.pid(self.a),collection)
        self.command(self.a,'cpu_match',club_id='2',stadium=1)
        match=self.s.store.active_match(self.pid(self.a))
        self.assertEqual(match['rosters'][0]['name'],'Selected second team')
        self.assertEqual(match['rosters'][0]['characters'][0]['boufbowlerClass'],14)
        self.assertEqual(self.s.collection(self.pid(self.a))['active'],'2')

    def test_unowned_team_cannot_join_queue_or_mutate_selection(self):
        with self.assertRaises(ServiceError):self.command(self.a,club_id='999')
        self.assertEqual(self.s.collection(self.pid(self.a))['active'],'1')
        self.assertEqual(self.s.matchmaking_status(self.pid(self.a))['status'],'idle')

    def test_v3_queue_migration_preserves_waiting_device(self):
        self.command(self.a)
        self.s.close()
        with sqlite3.connect(self.path) as db:
            db.executescript('ALTER TABLE matchmaking_queue RENAME TO queue_new;'
                'CREATE TABLE matchmaking_queue(profile_id TEXT PRIMARY KEY REFERENCES profiles(id),stadiums_json TEXT NOT NULL,joined REAL NOT NULL,heartbeat REAL NOT NULL);'
                'INSERT INTO matchmaking_queue SELECT profile_id,stadiums_json,joined,heartbeat FROM queue_new;'
                'DROP TABLE queue_new;DELETE FROM schema_versions WHERE version=4;')
        db.close()
        self.s=Service(self.path,self.config)
        status=self.s.matchmaking_status(self.pid(self.a))
        self.assertEqual(status['status'],'waiting')
        self.assertIsNone(status['tournament'])
        self.assertEqual(self.s.store.db.execute('SELECT MAX(version) FROM schema_versions').fetchone()[0],4)
        self.command(self.b)
        self.assertIsNotNone(self.s.store.active_match(self.pid(self.a)))
