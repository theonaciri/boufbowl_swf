"""Configurable leagues and optional seasonal ledgers, independent of practice."""
import json
import time
from backend.storage import ServiceError

DEFAULTS={'qualifying_games':3,'leagues':[{'id':5,'min_rating':0},{'id':4,'min_rating':1000},{'id':3,'min_rating':1100},{'id':2,'min_rating':1200},{'id':1,'min_rating':1400}],
          'seasons':{'enabled':False,'start_time':1791936000,'duration_seconds':2419200,'initial_rating':1000}}


class Progression:
    def public_ladder(self, page=1):
        if isinstance(page, str) and page.isascii() and page.isdigit() and len(page) <= 10:
            page = int(page)
        if isinstance(page, bool) or not isinstance(page, int) or not 1 <= page <= 2147483647:
            raise ServiceError('PAGE_INVALID', 'Choisissez une page de classement valide.')
        with self.store.transaction():
            self.maintain_progression()
            total = self.store.db.execute('SELECT COUNT(*) FROM profiles').fetchone()[0]
            pages = max(1, (total + 9) // 10)
            page = min(page, pages)
            rows = self.rankings((page - 1) * 10, 10)
            return {'ok': True, 'page': page, 'page_size': 10, 'total': total, 'pages': pages,
                    'generated_at': time.time(),
                    'players': [{'rank': row['rank'], 'nickname': row['player']['nickname'],
                                 'club': row['player']['club']['clubName'], 'rating': row['rating'],
                                 'wins': row['wins'], 'draws': row['draws'], 'losses': row['losses'],
                                 'league': row['league'], 'qualified': row['qualified']} for row in rows]}

    def progression_settings(self):return self.config['general'].get('progression',DEFAULTS)

    def league_for(self, profile):
        stats=self.store.profile(profile)['statistics'];cfg=self.progression_settings()
        if sum(stats.get(k,0) for k in ('wins','draws','defeats'))<cfg['qualifying_games']:return 0
        eligible=[l for l in cfg['leagues'] if stats['rating']>=l['min_rating']]
        return max(eligible,key=lambda l:l['min_rating'])['id'] if eligible else 5

    def league_rows(self, league):return [r for r in self.rankings() if r['league']==league]

    def ranking_info(self, profile):
        stats=self.store.profile(profile)['statistics'];league=self.league_for(profile)
        rank=next((i for i,r in enumerate(self.league_rows(league),1) if r['player']['nickname']==self.store.profile(profile)['nickname']),0) if league else 0
        return {**{k:stats[k] for k in ('wins','draws','defeats')},'rank':rank,'league':league,'subLeague':(rank-1)//100+1 if rank else 0}

    def ladder(self, profile, name='LADDER_BY_NICK_REQUEST', payload=None):
        payload=payload or {'self':True};league=self.league_for(profile) or 5;target=profile;index=0
        if name=='LADDER_BY_LEAGUE_REQUEST':
            league=payload.get('league');subleague=payload.get('subLeague',1)
            if league not in (1,2,3,4,5) or not isinstance(subleague,int) or subleague<1:
                self.emit(profile,'LADDER_REQUEST_ERROR',{'error':1});return
            index=(subleague-1)*100
        elif not payload.get('self'):
            row=self.store.db.execute('SELECT id FROM profiles WHERE nickname=?',(payload.get('nickName',''),)).fetchone()
            if not row:self.emit(profile,'LADDER_REQUEST_ERROR',{'error':1});return
            target=row[0];league=self.league_for(target) or 5
        rows=self.league_rows(league)
        rows=[{**r,'index':i,'rank':i+1} for i,r in enumerate(rows)]
        if name!='LADDER_BY_LEAGUE_REQUEST':index=next((i for i,r in enumerate(rows) if r['player']['nickname']==self.store.profile(target)['nickname']),0)
        start=(index//100)*100;subleague=index//100+1
        if start and start>=len(rows):self.emit(profile,'LADDER_REQUEST_ERROR',{'error':1});return
        own=next((r for r in rows if r['player']['nickname']==self.store.profile(profile)['nickname']),None)
        packet={'firstIndexToDisplay':index-start,'rows':[{k:v for k,v in r.items() if k not in ('league','qualified')} for r in rows[start:start+100]],
                'league':league,'subLeague':subleague,'leagueInformations':[{'league':n,'nonEmptySubleagues':list(range(1,(len(self.league_rows(n))+99)//100+1)) or [1]} for n in range(1,6)]}
        own=own or next(r for r in self.rankings() if r['player']['nickname']==self.store.profile(profile)['nickname'])
        own={**own,'rank':self.ranking_info(profile)['rank'],'index':max(0,self.ranking_info(profile)['rank']-1)}
        packet['ownData']={k:v for k,v in own.items() if k not in ('league','qualified')}
        self.emit(profile,'LADDER_DATA',packet)

    def current_season(self):
        cfg=self.progression_settings()['seasons']
        if not cfg['enabled'] or time.time()<cfg['start_time']:return None
        return 1+int((time.time()-cfg['start_time'])//cfg['duration_seconds'])

    def maintain_progression(self):
        season=self.current_season()
        if season is None:return
        cfg=self.progression_settings()['seasons']
        self.store.db.execute('INSERT OR IGNORE INTO seasons VALUES(?,?,NULL)',(season,json.dumps(cfg)))
        for row in self.store.db.execute('SELECT id,statistics_json FROM profiles').fetchall():
            stats=json.loads(row['statistics_json']);previous=stats.get('season_id')
            if previous==season:continue
            if previous is not None:
                self.store.db.execute('INSERT OR REPLACE INTO season_rankings VALUES(?,?,?)',(previous,row['id'],json.dumps({k:stats[k] for k in ('wins','draws','defeats','rating')})))
                self.store.db.execute('UPDATE seasons SET closed=COALESCE(closed,?) WHERE id=?',(time.time(),previous))
            stats.update(season_id=season,wins=0,draws=0,defeats=0,rating=cfg['initial_rating'])
            self.store.db.execute('UPDATE profiles SET statistics_json=? WHERE id=?',(json.dumps(stats),row['id']))
            self.emit_ranking(row['id'])

    def progression_data(self, profile):
        stats=self.store.profile(profile)['statistics']
        history=[{'season':r['season_id'],**json.loads(r['statistics_json'])} for r in self.store.db.execute('SELECT * FROM season_rankings WHERE profile_id=? ORDER BY season_id DESC',(profile,))]
        return {'ranking':self.ranking_info(profile),'rating':stats['rating'],'qualifying_games':self.progression_settings()['qualifying_games'],
                'leagues':self.progression_settings()['leagues'],'season':self.current_season(),'season_history':history}
