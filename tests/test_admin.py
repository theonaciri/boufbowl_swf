"""Console access, conversation isolation, sanctions and tournament persistence."""
import json
import time
import unittest
from backend.service import Service
from backend.storage import ServiceError
from tests import test_backend as helpers
initial_club = helpers.initial_club


class AdminTests(unittest.TestCase):
    setUp = helpers.BackendTests.setUp
    tearDown = helpers.BackendTests.tearDown
    identity = helpers.BackendTests.identity

    def grant(self, player, role='admin'):
        self.service.store.db.execute('INSERT OR REPLACE INTO profile_roles VALUES(?,?)', (self.identity(player),role))

    def api(self, action='messages', account=None, **fields):
        return self.service.admin({'session': (account or self.alice)['session'], 'action': action, **fields})

    def message(self, sender, text, recipient=None, match=None, language='en'):
        return self.service.store.db.execute('INSERT INTO chat_messages(sender,recipient,match_id,message,created,language) VALUES(?,?,?,?,?,?)',
            (self.identity(sender), self.identity(recipient) if recipient else None, match,text,time.time(), language if not recipient and not match else None)).lastrowid

    def settings(self, **changes):
        cfg = dict(name='Test cup',start_time=int(time.time())+3600,duration_seconds=2700,repeat_seconds=86400,
                   stadium=1,format='league',min_rating=900,max_rating=1100,
                   match_rules={'turns_per_match':8,'turns_per_period':4,'planning_seconds':15,'regenerate_between_turns':False},
                   prizes={'coins':250,'glory':50,'influence':10})
        cfg.update(changes)
        return cfg

    def allow_future_schedule(self):
        self.service.store.db.execute("UPDATE tournaments SET phase='ended',final_entries_json='[]'")
        # The persisted default instance is retained, so maintenance cannot recreate it.

    def test_authorization_for_private_data_and_schedules(self):
        with self.assertRaises(ServiceError): self.api()
        self.grant(self.alice,'moderator')
        self.assertTrue(self.api()['ok'])
        for action in ('tournaments','schedule'):
            with self.assertRaises(ServiceError): self.api(action,settings=self.settings())
        with self.assertRaises(ServiceError): self.api('suspend',nickname='Bob',duration=0)

    def test_private_context_is_bidirectional_and_ignores_other_filters(self):
        self.grant(self.alice)
        carol=self.service.hello({'nickname':'Carol','clubs':[initial_club()]})
        first=self.message(self.alice,'hello',self.bob)
        second=self.message(self.bob,'reply',self.alice)
        self.message(self.bob,'unrelated secret',carol)
        self.message(self.alice,'public')
        rows=self.api(focus=first,search='does not match',kind='public')['messages']
        self.assertEqual([r['id'] for r in rows],[second,first])
        self.assertEqual(len(self.api(kind='private')['messages']),3)
        self.assertEqual(len(self.api(kind='public')['messages']),1)
        self.assertEqual(len(self.api(player='carol')['messages']),1)
        self.assertEqual(len(self.api(search='secret')['messages']),1)

    def test_match_context_and_cursor_pagination(self):
        self.grant(self.alice)
        with self.service.store.transaction():
            match=self.service.create_match(self.identity(self.alice),self.identity(self.bob),1)
        first=self.message(self.alice,'match one',match=match['id'])
        second=self.message(self.bob,'match two',match=match['id'])
        self.message(self.alice,'not match')
        self.assertEqual([r['id'] for r in self.api(focus=first)['messages']],[second,first])
        self.assertEqual([r['id'] for r in self.api(focus=first,before=second)['messages']],[first])
        for i in range(102): self.message(self.alice,str(i))
        data=self.api(kind='public')
        self.assertEqual(len(data['messages']),100);self.assertTrue(data['has_more'])
        self.assertEqual(len(self.api(kind='public',before=data['messages'][-1]['id'])['messages']),3)
        with self.assertRaises(ServiceError): self.api(kind='invalid')
        with self.assertRaises(ServiceError): self.api(focus=True)

    def test_suspension_expiry_permanence_lifting_and_audit(self):
        self.grant(self.alice)
        for duration in (86400,604800,0):
            result=self.api('suspend',nickname='Bob',duration=duration,reason='Abusive chat')
            if duration:self.assertAlmostEqual(result['expires']-time.time(),duration,delta=2)
            else:self.assertIsNone(result['expires'])
            with self.assertRaisesRegex(ServiceError,'Abusive chat'):self.identity(self.bob)
            self.api('unsuspend',nickname='Bob',reason='Reviewed')
            self.identity(self.bob)
        self.assertEqual(len(self.api('moderation')['audit']),6)
        with self.assertRaises(ServiceError):self.api('suspend',nickname='Alice',duration=86400)
        with self.assertRaises(ServiceError):self.api('suspend',nickname='Bob',duration=3600)
        self.api('suspend',nickname='Bob',duration=86400)
        self.service.store.db.execute('UPDATE sanctions SET expires=?',(time.time()-1,))
        self.identity(self.bob)

    def test_schedule_validation_preserves_current_and_rolls_back(self):
        self.grant(self.alice)
        with self.assertRaises(ServiceError):self.api('schedule',settings=self.settings())
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM admin_settings').fetchone()[0],0)
        self.allow_future_schedule()
        for changes in [dict(min_rating=2000,max_rating=1000),dict(repeat_seconds=100),dict(start_time=0),
                        dict(format='elimination',qualification_seconds=2700),dict(stadium=True),
                        dict(prizes={'coins':-1}),dict(match_rules={'turns_per_match':1,'turns_per_period':2}),
                        dict(match_rules={'unimplemented_rule':1})]:
            with self.subTest(changes=changes):
                with self.assertRaises(ServiceError):self.api('schedule',settings=self.settings(**changes))
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM admin_events').fetchone()[0],0)

    def test_recurring_schedule_survives_restart_and_replaces_upcoming(self):
        self.grant(self.alice);self.allow_future_schedule()
        data=self.api('schedule',settings=self.settings())
        upcoming=[e for e in data['tournaments'] if e['phase']=='upcoming']
        self.assertEqual(len(upcoming),4)
        self.assertEqual(upcoming[0]['settings']['prizes']['coins'],250)
        self.assertEqual(len([e for e in data['tournaments'] if e['phase']=='ended']),1)
        self.service.close();self.service=Service(self.path,self.config)
        self.assertEqual(self.api('tournaments')['schedule']['name'],'Test cup')
        data=self.api('schedule',settings=self.settings(name='One-off',repeat_seconds=0))
        self.assertEqual(len([e for e in data['tournaments'] if e['phase']=='upcoming']),1)
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM admin_events').fetchone()[0],2)

    def test_rating_limits_and_special_rules_are_enforced(self):
        self.grant(self.alice);self.allow_future_schedule()
        self.api('schedule',settings=self.settings(repeat_seconds=0))
        cfg=self.service.tournament_settings();cfg.update(start_time=time.time()-60,end_time=time.time()+3600)
        self.service.store.db.execute('UPDATE tournaments SET settings_json=?,phase=\'open\' WHERE id=?',(json.dumps(cfg),cfg['id']))
        stats=self.service.store.profile(self.identity(self.bob))['statistics'];stats['rating']=800
        self.service.store.db.execute('UPDATE profiles SET statistics_json=? WHERE id=?',(json.dumps(stats),self.identity(self.bob)))
        with self.assertRaisesRegex(ServiceError,'rating'):self.service.join_queue(self.identity(self.bob),tournament=cfg['id'])
        stats['rating']=1000;self.service.store.db.execute('UPDATE profiles SET statistics_json=? WHERE id=?',(json.dumps(stats),self.identity(self.bob)))
        with self.service.store.transaction():
            self.service.join_queue(self.identity(self.alice),tournament=cfg['id'])
            self.service.join_queue(self.identity(self.bob),tournament=cfg['id'])
        match=self.service.store.active_match(self.identity(self.alice))
        self.assertEqual(match['rules']['match']['turns_per_match'],8)
        self.assertEqual(match['rules']['match']['planning_seconds'],15)
        self.assertFalse(match['rules']['match']['regenerate_between_turns'])
        self.assertEqual(self.service.config['rules']['match']['turns_per_match'],2)
        match['phase']='ended';match['score']=[1,0]
        with self.service.store.transaction():
            self.service.store.save_match(match)
            row=self.service.store.db.execute('SELECT * FROM tournaments WHERE id=?',(cfg['id'],)).fetchone()
            self.service.finalize_tournament(row)
            self.service.finalize_tournament(row)
        wallet=self.service.store.profile(self.identity(self.alice))['statistics']['tournament_wallet']
        self.assertEqual(wallet,{'coins':250,'glory':50,'influence':10})

    def test_asset_review_requires_administrator_and_upload_routes_reject_origin_and_filename(self):
        from functools import partial
        from http.server import ThreadingHTTPServer
        from threading import Thread
        from urllib.request import Request,urlopen
        from urllib.error import HTTPError
        import tempfile
        from backend.server import Handler
        from backend.asset_contributions import AssetContributions,catalog
        from tools.game_config import ROOT
        with tempfile.TemporaryDirectory() as folder:
            manager=AssetContributions(ROOT,folder,scanner=lambda *_:'test',start=False)
            self.service.asset_contributions=manager
            server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT)))
            server.service=self.service
            thread=Thread(target=server.serve_forever,daemon=True);thread.start()
            def post(route,body=None,headers=None,data=None):
                request=Request(f'http://127.0.0.1:{server.server_port}'+route,data=data if data is not None else json.dumps(body).encode(),headers={'X-Requested-With':'BoufbowlAssets','Content-Type':'application/json',**(headers or {})})
                try:
                    with urlopen(request) as response:return response.status,json.load(response)
                except HTTPError as error:
                    with error:return error.code,json.load(error)
            try:
                with self.assertRaises(ServiceError):self.api('assets')
                self.grant(self.alice,'moderator')
                with self.assertRaises(ServiceError):self.api('assets')
                response,_=post('/api/asset-preview',{'session':self.alice['session'],'id':'a'*32})
                self.assertEqual(response,403)
                self.grant(self.alice,'admin')
                self.assertTrue(self.api('assets')['ok'])
                item=next(iter(catalog(ROOT).values()))
                response,_=post('/api/asset-token',{'asset':item['id'],'consent':True,'contact':'Discord : Testeur'},{'Origin':'https://untrusted.example'})
                self.assertEqual(response,403)
                response,_=post('/api/asset-token',{'asset':item['id'],'consent':True})
                self.assertEqual(response,400)
                response,nonce=post('/api/asset-token',{'asset':item['id'],'consent':True,'contact':'Discord : Testeur'})
                self.assertEqual(response,200)
                response,_=post('/api/asset-upload',headers={'X-Asset-Id':item['id'],'X-Asset-Token':nonce['token'],'X-Asset-Name':'../'+item['name']},data=b'wrong')
                self.assertEqual(response,400)
                self.assertEqual(manager.db.execute('SELECT COUNT(*) FROM submissions').fetchone()[0],0)
            finally:
                server.shutdown();server.server_close();thread.join();manager.close()
