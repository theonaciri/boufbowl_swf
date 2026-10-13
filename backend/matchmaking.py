"""Persistent human queue, bounded searches and rating-aware pairing."""
import json
import time
from backend.storage import ServiceError
from tools.game_config import STADIUMS

DEFAULTS={'rating_window':200,'widen_per_second':5,'heartbeat_timeout':30,'search_timeout':300}


class Matchmaking:
    def matchmaking_settings(self):
        return {**DEFAULTS,**self.config['general'].get('matchmaking',{})}

    def leave_queue(self, profile):
        self.store.db.execute('DELETE FROM matchmaking_queue WHERE profile_id=?',(profile,))

    def join_queue(self, profile, stadiums=None):
        if self.store.active_match(profile):
            raise ServiceError('MATCH_ACTIVE','Finish your current match before searching')
        enabled={i for i,name in enumerate(STADIUMS,1) if self.config['stadiums'][name]['enabled']}
        if stadiums is None: stadiums=sorted(enabled)
        if not isinstance(stadiums,list) or not stadiums or any(not isinstance(i,int) or isinstance(i,bool) or i not in enabled for i in stadiums):
            raise ServiceError('INVALID_STADIUM','Choose one or more enabled stadiums')
        if self.spectator_match(profile):
            raise ServiceError('PLAYER_BUSY','Stop spectating before searching')
        self.cancel_challenges(profile)
        now=time.time()
        self.store.db.execute('INSERT INTO matchmaking_queue VALUES(?,?,?,?) ON CONFLICT(profile_id) DO UPDATE SET stadiums_json=excluded.stadiums_json,heartbeat=excluded.heartbeat',
                              (profile,json.dumps(sorted(set(stadiums))),now,now))
        self.match_queued_players()

    def match_queued_players(self):
        now=time.time(); settings=self.matchmaking_settings()
        self.store.db.execute('DELETE FROM matchmaking_queue WHERE heartbeat<? OR joined<?',
                              (now-settings['heartbeat_timeout'],now-settings['search_timeout']))
        rows=self.store.db.execute('SELECT * FROM matchmaking_queue ORDER BY joined,profile_id').fetchall()
        available=[]
        for row in rows:
            if self.store.active_match(row['profile_id']): self.leave_queue(row['profile_id']);continue
            available.append(row)
        matched=set()
        for i,first in enumerate(available):
            if first['profile_id'] in matched: continue
            rating=self.store.profile(first['profile_id'])['statistics']['rating']
            choices=[]
            for second in available[i+1:]:
                if second['profile_id'] in matched or self.blocked(first['profile_id'], second['profile_id']): continue
                common=set(json.loads(first['stadiums_json'])) & set(json.loads(second['stadiums_json']))
                common={n for n in common if self.config['stadiums'][STADIUMS[n-1]]['enabled']}
                if not common: continue
                distance=abs(rating-self.store.profile(second['profile_id'])['statistics']['rating'])
                window=settings['rating_window']+settings['widen_per_second']*(now-min(first['joined'],second['joined']))
                if distance<=window: choices.append((distance,second['joined'],second['profile_id'],second,min(common)))
            if choices:
                _,_,_,second,stadium=min(choices,key=lambda c:c[:3])
                self.create_match(first['profile_id'],second['profile_id'],stadium)
                matched.update((first['profile_id'],second['profile_id']))

    def matchmaking_status(self, profile):
        row=self.store.db.execute('SELECT * FROM matchmaking_queue WHERE profile_id=?',(profile,)).fetchone()
        return {'status':'waiting' if row else 'idle', 'joined':row['joined'] if row else None,
                'stadiums':json.loads(row['stadiums_json']) if row else [],
                'waiting_players':self.store.db.execute('SELECT COUNT(*) FROM matchmaking_queue').fetchone()[0]}
