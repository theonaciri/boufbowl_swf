"""Persistent human queue, bounded searches and rating-aware pairing."""
import json
import time
from backend.storage import ServiceError
from tools.game_config import STADIUMS

DEFAULTS={'rating_window':200,'widen_per_second':5,'heartbeat_timeout':90,'search_timeout':300}


class Matchmaking:
    def matchmaking_settings(self):
        return {**DEFAULTS,**self.config['general'].get('matchmaking',{})}

    def leave_queue(self, profile):
        self.store.db.execute('DELETE FROM matchmaking_queue WHERE profile_id=?',(profile,))

    def join_queue(self, profile, stadiums=None, tournament=None):
        if self.store.active_match(profile):
            raise ServiceError('MATCH_ACTIVE','Finish your current match before searching')
        if tournament is not None:
            settings=self.tournament_config(tournament)
            if not settings['start_time'] <= time.time() < settings['end_time']:
                raise ServiceError('TOURNAMENT_CLOSED','This tournament is outside its configured time window')
            rating=self.store.profile(profile)['statistics']['rating']
            if not settings.get('min_rating',0)<=rating<=settings.get('max_rating',100000):
                raise ServiceError('TOURNAMENT_RATING','Your rating is outside this tournament’s allowed range')
            self.knockout_eligible(profile,settings)
            stadiums=[settings['stadium']]
            tournament=str(settings['id'])
        enabled={i for i,name in enumerate(STADIUMS,1) if self.config['stadiums'][name]['enabled']}
        if stadiums is None: stadiums=sorted(enabled)
        if not isinstance(stadiums,list) or not stadiums or any(not isinstance(i,int) or isinstance(i,bool) or i not in enabled for i in stadiums):
            raise ServiceError('INVALID_STADIUM','Choose one or more enabled stadiums')
        if self.spectator_match(profile):
            raise ServiceError('PLAYER_BUSY','Stop spectating before searching')
        self.cancel_challenges(profile)
        now=time.time()
        self.store.db.execute('INSERT INTO matchmaking_queue(profile_id,stadiums_json,joined,heartbeat,tournament_id) VALUES(?,?,?,?,?) ON CONFLICT(profile_id) DO UPDATE SET stadiums_json=excluded.stadiums_json,joined=CASE WHEN matchmaking_queue.tournament_id IS excluded.tournament_id THEN matchmaking_queue.joined ELSE excluded.joined END,heartbeat=excluded.heartbeat,tournament_id=excluded.tournament_id',
                              (profile,json.dumps(sorted(set(stadiums))),now,now,tournament))
        if tournament is not None: self.register_tournament(profile,settings)
        self.match_queued_players()

    def match_queued_players(self):
        now=time.time(); settings=self.matchmaking_settings()
        expired=self.store.db.execute('SELECT profile_id,tournament_id FROM matchmaking_queue WHERE heartbeat<? OR joined<?',(now-settings['heartbeat_timeout'],now-settings['search_timeout'])).fetchall()
        for entry in expired:
            if entry['tournament_id'] is not None:self.emit(entry['profile_id'],'TOURNAMENT_OFFER_CANCELED',{})
        self.store.db.execute('DELETE FROM matchmaking_queue WHERE heartbeat<? OR joined<?',
                              (now-settings['heartbeat_timeout'],now-settings['search_timeout']))
        rows=self.store.db.execute('SELECT * FROM matchmaking_queue ORDER BY joined,profile_id').fetchall()
        available=[]
        for row in rows:
            if self.store.active_match(row['profile_id']): self.leave_queue(row['profile_id']);continue
            if row['tournament_id'] is not None:
                try:
                    tournament=self.tournament_config(row['tournament_id'])
                    if not tournament['start_time'] <= now < tournament['end_time']: raise ServiceError('TOURNAMENT_CLOSED','Tournament ended')
                except ServiceError:
                    self.leave_queue(row['profile_id']);continue
            available.append(row)
        matched=set()
        for i,first in enumerate(available):
            if first['profile_id'] in matched: continue
            rating=self.store.profile(first['profile_id'])['statistics']['rating']
            choices=[]
            for second in available[i+1:]:
                if second['profile_id'] in matched or self.blocked(first['profile_id'], second['profile_id']): continue
                if first['tournament_id'] != second['tournament_id']: continue
                if first['tournament_id'] is not None and not self.knockout_pair_allowed(first['tournament_id'],first['profile_id'],second['profile_id']):continue
                common=set(json.loads(first['stadiums_json'])) & set(json.loads(second['stadiums_json']))
                common={n for n in common if self.config['stadiums'][STADIUMS[n-1]]['enabled']}
                if not common: continue
                distance=abs(rating-self.store.profile(second['profile_id'])['statistics']['rating'])
                window=settings['rating_window']+settings['widen_per_second']*(now-min(first['joined'],second['joined']))
                if distance<=window: choices.append((distance,second['joined'],second['profile_id'],second,min(common)))
            if choices:
                _,_,_,second,stadium=min(choices,key=lambda c:c[:3])
                self.create_match(first['profile_id'],second['profile_id'],stadium, tournament=int(first['tournament_id']) if first['tournament_id'] is not None else None, source="tournament" if first['tournament_id'] is not None else "matchmaking")
                matched.update((first['profile_id'],second['profile_id']))

    def matchmaking_status(self, profile):
        row=self.store.db.execute('SELECT * FROM matchmaking_queue WHERE profile_id=?',(profile,)).fetchone()
        return {'status':'waiting' if row else 'idle', 'joined':row['joined'] if row else None,
                'stadiums':json.loads(row['stadiums_json']) if row else [],
                'tournament':row['tournament_id'] if row else None,
                'waiting_players':self.store.db.execute('SELECT COUNT(*) FROM matchmaking_queue').fetchone()[0]}
