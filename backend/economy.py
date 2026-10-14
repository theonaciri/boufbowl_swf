"""Local cosmetic ownership and atomic currency spending; free mode stays available."""
import json
import time
from backend.storage import ServiceError
from tools.game_config import ROOT

CURRENCIES=('glory','influence','coins')


class Economy:
    def cosmetic_catalog(self):
        catalog=json.loads((ROOT/'resources/cosmetic_catalog.json').read_text())
        palettes=json.loads((ROOT/'resources/palettes.json').read_text())
        ids=set()
        for item in catalog:
            allowed=palettes['club_palettes' if item['kind']=='club_palette' else 'character_palettes']
            if item['id'] in ids or item['kind'] not in ('club_palette','character_palette') or item['asset_id'] not in {p['id'] for p in allowed}:
                raise ServiceError('CATALOG_INVALID','Invalid cosmetic catalog identity or asset')
            ids.add(item['id'])
            if any(k not in CURRENCIES or not isinstance(v,int) or isinstance(v,bool) or not 0<=v<=1000000000 for k,v in item['price'].items()):
                raise ServiceError('CATALOG_INVALID','Invalid cosmetic catalog price')
        return catalog

    def economy_settings(self):return self.config['general'].get('economy',{'free_customization':True})

    def wallet_data(self, profile):
        stats=self.store.profile(profile)['statistics'];wallet={k:stats.get('tournament_wallet',{}).get(k,0) for k in CURRENCIES}
        owned={r[0] for r in self.store.db.execute('SELECT item_id FROM cosmetic_unlocks WHERE profile_id=?',(profile,))}
        free=self.economy_settings()['free_customization']
        catalog=[{**item,'owned':item['id'] in owned,'available':free or item['id'] in owned,'price':{} if free else item['price'],'list_price':item['price']} for item in self.cosmetic_catalog()]
        awards=[{'tournament':r['tournament_id'],'reward':r['reward'],'amount':json.loads(r['balances_json']),'created':r['awarded']} for r in self.store.db.execute('SELECT * FROM tournament_rewards WHERE profile_id=? ORDER BY awarded DESC LIMIT 50',(profile,))]
        purchases=[{'item':r['item_id'],'amount':json.loads(r['amount_json']),'created':r['created']} for r in self.store.db.execute('SELECT * FROM economy_ledger WHERE profile_id=? ORDER BY id DESC LIMIT 50',(profile,))]
        return {'wallet':wallet,'catalog':catalog,'awards':awards,'purchases':purchases,'free_customization':free}

    def buy_cosmetic(self, profile, identity):
        item=next((i for i in self.cosmetic_catalog() if i['id']==identity),None)
        if not item:raise ServiceError('COSMETIC_UNKNOWN','Unknown cosmetic item')
        if self.store.db.execute('SELECT 1 FROM cosmetic_unlocks WHERE profile_id=? AND item_id=?',(profile,identity)).fetchone():return self.wallet_data(profile)
        price={} if self.economy_settings()['free_customization'] else item['price']
        stats=self.store.profile(profile)['statistics'];wallet=stats.setdefault('tournament_wallet',{k:0 for k in CURRENCIES})
        if any(wallet.get(k,0)<v for k,v in price.items()):raise ServiceError('FUNDS_INSUFFICIENT','Not enough local currency')
        for key,amount in price.items():wallet[key]=wallet.get(key,0)-amount
        self.store.db.execute('INSERT INTO cosmetic_unlocks VALUES(?,?,?)',(profile,identity,time.time()))
        self.store.db.execute('INSERT INTO economy_ledger(profile_id,item_id,amount_json,created) VALUES(?,?,?,?)',(profile,identity,json.dumps(price),time.time()))
        self.store.db.execute('UPDATE profiles SET statistics_json=? WHERE id=?',(json.dumps(stats),profile))
        self.emit(profile,'PREMIUM_CONTENT_UPDATED',{})
        return self.wallet_data(profile)

    def enforce_cosmetics(self, profile, club):
        if self.economy_settings()['free_customization']:return
        selected={('club_palette',club.get('paletteId'))}
        selected.update(('character_palette',p.get('paletteId')) for p in club.get('boufbowler',[]))
        owned={r[0] for r in self.store.db.execute('SELECT item_id FROM cosmetic_unlocks WHERE profile_id=?',(profile,))}
        for item in self.cosmetic_catalog():
            if (item['kind'],item['asset_id']) in selected and item['id'] not in owned:
                raise ServiceError('COSMETIC_LOCKED','Unlock '+item['name']+' in the cosmetic catalog')

    def news_data(self, profile):
        language=self.channel_state(profile)['language']
        settings=self.config['general'].get('news',{'title':{'en':'Boufbowl'},'body':{'en':'Welcome to the local game.'}})
        next_event=self.store.db.execute("SELECT id,settings_json FROM tournaments WHERE phase='upcoming' ORDER BY id LIMIT 1").fetchone()
        return {'title':settings['title'].get(language,settings['title']['en']),'body':settings['body'].get(language,settings['body']['en']),
                'role':self.role(profile),'running_tournament':self.current_tournament_id(),
                'next_tournament':{'id':str(next_event['id']),**json.loads(next_event['settings_json'])} if next_event else None,
                'progression':self.progression_data(profile)}
