import json
import tempfile
from pathlib import Path
import time
import unittest
from unittest.mock import patch
from backend.service import Service
from backend.storage import ServiceError
from tests.test_backend import initial_club
from tools.game_config import load_config


class TournamentRoundTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.now=int(time.time());self.anchor=self.now
        self.clock=patch('backend.tournaments.time.time',side_effect=lambda:self.now);self.clock.start()
        self.cfg=load_config();self.cfg['general']['cinematics']['introductions']=False
        self.cfg['general']['tournament'].update(format='elimination',id=1,start_time=self.anchor,end_time=self.anchor+30,repeat_seconds=0,
            qualification_seconds=10,qualifying_top=4,round_count=2,round_seconds=10,stadium_rotation=[1])
        self.service=Service(Path(self.tmp.name)/'state.sqlite',self.cfg);self.service.stopping.set();self.service.maintenance.join()
        self.players={n:self.service.hello({'nickname':n,'clubs':[initial_club()]}) for n in ('Alice','Bob','Carol','Dave')}

    def tearDown(self):self.service.close();self.clock.stop();self.tmp.cleanup()
    def pid(self,n):return self.service.store.authenticate(self.players[n]['session'])
    def join(self,n):
        with self.service.store.transaction():self.service.tournament_match(self.pid(n),1)
    def advance(self,delta):
        self.now=self.anchor+delta
        with self.service.store.transaction():self.service.maintain_tournaments()
    def win(self,n):
        match=self.service.store.active_match(self.pid(n));match['score']=[0,0];match['score'][match['profiles'].index(self.pid(n))]=1
        with self.service.store.transaction():self.service.end_match(match)
    def qualify(self):
        for n in ('Alice','Bob','Carol','Dave'):self.join(n)
        self.win('Alice');self.win('Carol');self.advance(10)

    def test_bracket_pairing_two_rounds_elimination_and_final_standings(self):
        self.qualify();row,data=self.service.round_state(1)
        self.assertEqual(row['round'],1);self.assertEqual(len(data['pairs']),2)
        self.join('Alice');self.join('Carol')
        self.assertIsNone(self.service.store.active_match(self.pid('Alice')))
        self.join('Dave');self.join('Bob')
        self.assertEqual(self.service.store.active_match(self.pid('Alice'))['tournament_round'],1)
        self.win('Alice');self.win('Carol')
        with self.assertRaises(ServiceError):self.join('Alice')
        self.advance(20)
        with self.assertRaises(ServiceError):self.join('Bob')
        entries=dict(self.service.tournament_entries(self.service.tournament_config(1)))
        self.assertTrue(entries[self.pid('Bob')]['eliminated'])
        self.join('Alice');self.join('Carol');self.win('Alice');self.advance(30)
        row,data=self.service.round_state(1);self.assertEqual(row['phase'],'finished')
        entries=dict(self.service.tournament_entries(self.service.tournament_config(1)))
        self.assertEqual(entries[self.pid('Alice')]['currentRank'],1)
        self.assertEqual(entries[self.pid('Carol')]['currentRank'],2)
        self.assertEqual(self.service.store.db.execute('SELECT phase FROM tournaments WHERE id=1').fetchone()[0],'ended')
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM tournament_rewards').fetchone()[0],4)

    def test_late_qualification_finishes_before_advancement_and_shifts_rounds(self):
        self.join('Alice');self.join('Bob');self.advance(15)
        row,data=self.service.round_state(1);self.assertEqual(row['phase'],'closing')
        with self.assertRaises(ServiceError):self.join('Carol')
        self.win('Alice')
        row,data=self.service.round_state(1);self.assertEqual(row['round'],1)
        self.assertEqual(data['slot']['start'],self.anchor+15)
        self.assertEqual(self.service.tournament_config(1)['end_time'],self.anchor+35)

    def test_unplayed_registration_receives_no_qualification_or_reward(self):
        self.join('Alice');self.advance(10)
        self.assertEqual(self.service.store.db.execute('SELECT phase FROM tournaments WHERE id=1').fetchone()[0],'ended')
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM tournament_rewards').fetchone()[0],0)

    def test_draw_uses_qualification_seed_and_does_not_create_second_round_game(self):
        self.qualify()
        for n in ('Alice','Dave','Carol','Bob'):self.join(n)
        match=self.service.store.active_match(self.pid('Alice'));match['score']=[0,0]
        with self.service.store.transaction():self.service.end_match(match)
        self.win('Carol');self.advance(20)
        row,data=self.service.round_state(1)
        self.assertIn(self.pid('Alice'),data['eligible']);self.assertNotIn(self.pid('Dave'),data['eligible'])

    def test_late_round_holds_next_tournament_and_keeps_only_one_running(self):
        self.service.config['general']['tournament']['repeat_seconds']=40
        self.join('Alice');self.join('Bob');self.advance(45)
        self.assertEqual(self.service.current_tournament_id(),'1')
        next_event=self.service.tournament_config(2)
        self.assertGreater(next_event['start_time'],self.now)
        self.assertEqual(self.service.store.db.execute("SELECT COUNT(*) FROM tournaments WHERE phase='open'").fetchone()[0],1)

    def test_offline_or_cancelled_queue_cannot_earn_a_walkover(self):
        self.qualify();self.join('Alice')
        self.service.store.db.execute('UPDATE presence SET seen=? WHERE profile_id=?',(self.anchor-60,self.pid('Alice')))
        self.advance(20)
        _,bracket=self.service.round_state(1)
        self.assertEqual(bracket.get('champions'),[])
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM tournament_rewards').fetchone()[0],0)
