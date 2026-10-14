from copy import deepcopy
import json
import time
import unittest
from tests import test_backend as helpers
from backend.storage import ServiceError


class ProgressionEconomyTests(unittest.TestCase):
    setUp=helpers.BackendTests.setUp
    tearDown=helpers.BackendTests.tearDown
    identity=helpers.BackendTests.identity

    def stats(self,player,**values):
        profile=self.identity(player);stats=self.service.store.profile(profile)['statistics'];stats.update(values)
        self.service.store.db.execute('UPDATE profiles SET statistics_json=? WHERE id=?',(json.dumps(stats),profile));return profile

    def api(self,p,action,**fields):return self.service.community({'session':p['session'],'action':action,**fields})

    def test_qualification_all_five_leagues_and_promotion_relegation(self):
        profile=self.identity(self.alice);self.assertEqual(self.service.league_for(profile),0)
        for rating,league in ((900,5),(1000,4),(1100,3),(1200,2),(1400,1),(1300,2)):
            self.stats(self.alice,wins=3,rating=rating)
            self.assertEqual(self.service.league_for(profile),league)
            self.assertEqual(self.service.ranking_info(profile)['league'],league)
        self.stats(self.alice,wins=0,rating=1800,practice={'wins':20,'draws':0,'defeats':0})
        self.assertEqual(self.service.league_for(profile),0)

    def test_native_ladder_filters_leagues_and_unranked_self_has_no_badge(self):
        a=self.stats(self.alice,wins=3,rating=1400);b=self.stats(self.bob,wins=3,rating=1000)
        self.service.ladder(a,'LADDER_BY_LEAGUE_REQUEST',{'league':4,'subLeague':1})
        packet=next(e for e in reversed(self.service.store.poll(a,0)) if e['type']=='LADDER_DATA')
        payload=self.service.codec.open_envelope(bytes.fromhex(packet['hex']))['payload']
        self.assertEqual([r['player']['nickname'] for r in payload['rows']],['Bob'])
        self.assertEqual(len(payload['leagueInformations']),5)
        self.assertEqual(payload['ownData']['player']['nickname'],'Alice')

    def test_season_rollover_archives_ranked_progress_and_keeps_wallet(self):
        cfg=self.service.config['general']['progression']['seasons'];now=int(time.time())
        cfg.update(enabled=True,start_time=now-1,duration_seconds=60)
        with self.service.store.transaction():self.service.maintain_progression()
        profile=self.stats(self.alice,wins=3,rating=1060,tournament_wallet={'glory':20,'influence':10,'coins':10})
        cfg['start_time']-=60
        with self.service.store.transaction():self.service.maintain_progression()
        data=self.api(self.alice,'progression')
        self.assertEqual(data['season'],2);self.assertEqual(data['season_history'][0]['wins'],3)
        stats=self.service.store.profile(profile)['statistics'];self.assertEqual(stats['wins'],0)
        self.assertEqual(stats['tournament_wallet']['coins'],10)

    def test_atomic_cosmetic_purchase_and_retry_charge_only_once(self):
        self.service.config['general']['economy']['free_customization']=False
        self.stats(self.alice,tournament_wallet={'glory':0,'influence':0,'coins':30})
        body={'session':self.alice['session'],'action':'buy','item_id':'pastel','request_id':'purchase'}
        first=self.service.community(body);self.assertEqual(first,self.service.community(body))
        self.assertEqual(first['wallet']['coins'],10)
        self.assertEqual(self.api(self.alice,'buy',item_id='pastel')['wallet']['coins'],10)
        with self.assertRaises(ServiceError):self.api(self.alice,'buy',item_id='vivid')
        self.assertEqual(self.service.store.db.execute('SELECT COUNT(*) FROM economy_ledger').fetchone()[0],1)

    def test_late_ranked_result_credits_its_original_season_once(self):
        cfg=self.service.config['general']['progression']['seasons'];now=int(time.time())
        cfg.update(enabled=True,start_time=now-1,duration_seconds=60)
        with self.service.store.transaction():self.service.maintain_progression()
        a=self.identity(self.alice);b=self.identity(self.bob)
        with self.service.store.transaction():
            match=self.service.create_match(a,b,1,source='matchmaking')
        self.assertEqual(match['season_id'],1)
        cfg['start_time']-=60
        with self.service.store.transaction():
            self.service.maintain_progression();match['score']=[1,0]
            self.service.end_match(match);self.service.end_match(match)
        current=self.service.store.profile(a)['statistics']
        self.assertEqual((current['season_id'],current['wins'],current['rating']),(2,0,1000))
        self.assertEqual(current['lifetime_ranked']['wins'],1)
        archive=self.service.progression_data(a)['season_history'][0]
        self.assertEqual((archive['season'],archive['wins'],archive['rating']),(1,1,1020))

    def test_paid_cosmetics_are_enforced_on_changes_and_free_mode_remains_available(self):
        self.service.config['general']['economy']['free_customization']=False
        club=deepcopy(self.service.club(self.identity(self.alice)));club['boufbowler'][0]['paletteId']=101
        with self.assertRaises(ServiceError):self.service.save_club(self.identity(self.alice),club)
        self.stats(self.alice,tournament_wallet={'glory':0,'influence':0,'coins':20})
        self.api(self.alice,'buy',item_id='pastel');self.service.save_club(self.identity(self.alice),club)
        self.service.config['general']['economy']['free_customization']=True
        free=self.api(self.alice,'buy',item_id='vivid');self.assertEqual(free['wallet']['coins'],0)
        self.assertTrue(all(i['available'] for i in free['catalog']))

    def test_news_uses_saved_language_and_current_schedule(self):
        self.service.touch(self.identity(self.alice),'fr')
        data=self.api(self.alice,'news');self.assertIn('Bienvenue',data['title'])
        self.assertIn('progression',data);self.assertEqual(data['role'],'player')

    def test_cosmetic_prices_are_server_owned_and_all_three_currencies_are_spendable(self):
        self.service.config['general']['economy']['free_customization']=False
        self.stats(self.alice,tournament_wallet={'glory':10,'influence':5,'coins':40})
        first=self.api(self.alice,'buy',item_id='club_sunset',price={'coins':0})
        self.assertEqual(first['wallet'],{'glory':0,'influence':5,'coins':25})
        second=self.api(self.alice,'buy',item_id='club_forest')
        self.assertEqual(second['wallet'],{'glory':0,'influence':0,'coins':15})
        with self.assertRaises(ServiceError):self.api(self.alice,'buy',item_id='natural')
        self.assertEqual(self.api(self.alice,'wallet')['wallet'],second['wallet'])
