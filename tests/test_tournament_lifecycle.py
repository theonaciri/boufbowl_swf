import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from backend.service import Service
from backend.matchmaking_metrics import report as queue_report
from backend.storage import ServiceError
from tests.test_backend import initial_club
from tools.game_config import load_config
from tools.tournament_text import update_tournament_text


class TournamentLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.path=Path(self.directory.name)/'state.sqlite'
        self.now=int(time.time());self.anchor=self.now+10
        self.clock=patch('backend.tournaments.time.time',side_effect=lambda:self.now);self.clock.start()
        self.config=load_config();self.config['general']['cinematics']['introductions']=False
        self.config['general']['tournament'].update(format='league',id=1,start_time=self.anchor,end_time=self.anchor+30,repeat_seconds=60,stadium_rotation=[3,5],rewards=[1,2,3,4])
        self.service=Service(self.path,self.config);self.service.stopping.set();self.service.maintenance.join()
        self.a=self.service.hello({'nickname':'Alice','clubs':[initial_club()]});self.b=self.service.hello({'nickname':'Bob','clubs':[initial_club()]})

    def tearDown(self):
        self.service.close();self.clock.stop();self.directory.cleanup()

    def pid(self,p):return self.service.store.authenticate(p['session'])

    def advance(self,now):
        self.now=now
        with self.service.store.transaction():self.service.maintain_tournaments()

    def packet(self,p,name):
        events=self.service.store.poll(self.pid(p),0)
        event=next(e for e in reversed(events) if e['type']==name)
        return self.service.codec.open_envelope(bytes.fromhex(event['hex']))['payload']

    def test_future_beginning_entry_end_and_next_instance(self):
        self.service.tournaments(self.pid(self.a))
        for identity in ({'id':1},True,'bad',-1,2**64):
            with self.assertRaises(ServiceError):self.service.tournament_config(identity)
        data=self.packet(self.a,'OUTSTANDING_TOURNAMENTS')
        self.assertEqual(len(data['tournaments']),3);self.assertIsNone(self.service.current_tournament_id())
        self.assertEqual(data['tournaments'][0]['startTime'],self.anchor*1000)
        with self.assertRaises(ServiceError):self.service.tournament_match(self.pid(self.a),1)
        self.advance(self.anchor);self.assertEqual(self.service.current_tournament_id(),'1')
        self.service.tournament_match(self.pid(self.a),1)
        self.assertEqual(self.service.matchmaking_status(self.pid(self.a))['status'],'waiting')
        self.advance(self.anchor+30)
        self.assertEqual(self.service.matchmaking_status(self.pid(self.a))['status'],'idle')
        exits=queue_report(self.service.store.db,'2000-01-01')['rows']
        self.assertEqual([(row['kind'],row['outcome'],row['count']) for row in exits], [('tournament','tournament_closed',1)])
        self.assertTrue(self.packet(self.a,'PAST_TOURNAMENTS')['tournaments'][0]['closed'])
        self.assertEqual(self.packet(self.a,'TOURNAMENT_CLOSED')['tournamentId'],'1')
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM tournament_rewards').fetchone()[0],0)
        self.advance(self.anchor+60)
        self.assertEqual(self.service.current_tournament_id(),'2');self.assertEqual(self.service.tournament_config(2)['stadium'],5)

    def test_late_finish_counts_then_finalizes_podium_and_rewards_once(self):
        self.advance(self.anchor)
        for p in (self.a,self.b):self.service.tournament_match(self.pid(p),1)
        match=self.service.store.active_match(self.pid(self.a));self.assertEqual(match['stadium'],3)
        self.advance(self.anchor+30)
        self.assertEqual(self.service.store.db.execute('SELECT phase FROM tournaments WHERE id=1').fetchone()[0],'closing')
        self.assertFalse(self.packet(self.a,'PAST_TOURNAMENTS')['tournaments'][0]['closed'])
        with self.assertRaises(ServiceError):self.service.tournament_match(self.pid(self.a),1)
        match['score']=[0,0];match['score'][match['profiles'].index(self.pid(self.a))]=1
        with self.service.store.transaction():self.service.end_match(match)
        entries=dict(self.service.tournament_entries(self.service.tournament_config(1)))
        self.assertEqual(entries[self.pid(self.a)]['tournamentPoints'],3)
        self.assertEqual(entries[self.pid(self.a)]['reward'],1)
        self.assertTrue(self.packet(self.a,'PAST_TOURNAMENTS')['tournaments'][0]['closed'])
        stats=self.service.store.profile(self.pid(self.a))['statistics']
        self.assertEqual(stats['tournament_wallet'],{'glory':20,'influence':10,'coins':10})
        self.service.close();self.service=Service(self.path,self.config);self.service.stopping.set();self.service.maintenance.join()
        self.advance(self.anchor+31)
        self.assertEqual(self.service.store.profile(self.pid(self.a))['statistics'],stats)
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM tournament_rewards').fetchone()[0],2)
        self.assertEqual(entries,dict(self.service.tournament_entries(self.service.tournament_config(1))))

    def test_clock_offset_does_not_replace_frozen_instance_settings(self):
        first=self.service.tournament_config(1)
        self.service.config['general']['tournament']['stadium_rotation']=[9]
        self.assertEqual(self.service.tournament_config(1),first)
        self.advance(self.anchor+120)
        self.assertEqual(self.service.tournament_config(5)['stadium'],9)

    def test_all_languages_localize_timer_name_and_reward_descriptions_idempotently(self):
        from tools.game_config import ROOT
        text=(ROOT/'resources/lang.json').read_text()
        updated=update_tournament_text(text)
        self.assertEqual(updated,update_tournament_text(updated))
        for phrase in ('Ends in $1','Fin dans $1','Endet in $1','Termina en $1','local currency','monnaie locale'):
            self.assertIn(phrase,updated)
