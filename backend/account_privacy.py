"""Account privacy operations. Exports are projections, never database/replay dumps."""
import hmac
import json
import secrets
import time
import uuid
from backend.storage import ServiceError


DELETION_NOTICE = ('Le compte, les sessions, les clubs, les messages et les liens sociaux sont supprimés. '
                   'Les résultats et tableaux de tournoi restent sous un pseudonyme pour préserver les autres joueurs. '
                   'Terminez ou abandonnez votre match avant de supprimer le profil.')


def privacy_action(service, body, peer):
    from backend.accounts import password_hash, ITERATIONS
    store = service.store
    error = None
    with store.transaction():
        profile = store.authenticate(body.get('session'))
        account = store.db.execute('SELECT * FROM accounts WHERE profile_id=?', (profile,)).fetchone()
        # The session determines ownership. A supplied username/profile_id is ignored.
        if account:
            bucket = store.digest(str(peer) + '|' + account['username'])
            attempt = store.db.execute('SELECT * FROM auth_attempts WHERE bucket=?', (bucket,)).fetchone()
            if attempt and attempt['reset_at'] > time.time() and attempt['failures'] >= 5:
                raise ServiceError('ACCOUNT_RATE_LIMIT', 'Trop de tentatives. Réessayez dans cinq minutes.')
            password = body.get('password')
            valid = isinstance(password, str) and 10 <= len(password) <= 128
            computed = password_hash(password if valid else '', account['salt'], account['iterations'] or ITERATIONS)
            if not valid or not hmac.compare_digest(computed, account['password_hash']):
                now = time.time()
                failures = attempt['failures'] + 1 if attempt and attempt['reset_at'] > now else 1
                reset = attempt['reset_at'] if attempt and attempt['reset_at'] > now else now + 300
                store.db.execute('INSERT OR REPLACE INTO auth_attempts VALUES(?,?,?)', (bucket, failures, reset))
                error = ServiceError('ACCOUNT_AUTH', 'Confirmez le mot de passe du compte lié à ce profil.')
            else:
                store.db.execute('DELETE FROM auth_attempts WHERE bucket=?', (bucket,))
        if error is None:
            if body['action'] == 'export':
                result = {'ok': True, 'export': export_personal_data(service, profile, account)}
            else:
                player = store.profile(profile)
                if body.get('confirmation') != 'SUPPRIMER' or body.get('nickname') != player['nickname']:
                    raise ServiceError('ACCOUNT_CONFIRMATION', 'Saisissez votre pseudo exact et SUPPRIMER pour confirmer.')
                if store.active_match(profile):
                    raise ServiceError('ACCOUNT_MATCH_ACTIVE', 'Terminez ou abandonnez votre match avant la suppression.')
                clear = {}
                for field in ('device_session', 'account_session'):
                    token = body.get(field)
                    clear['clear_' + field] = bool(isinstance(token, str) and store.db.execute(
                        'SELECT 1 FROM sessions WHERE token_hash=? AND profile_id=?',
                        (store.digest(token), profile)).fetchone())
                delete_personal_data(service, profile)
                result = {'ok': True, 'deleted': True, 'notice': DELETION_NOTICE, **clear}
    # Commit bad-password counters before reporting failure.
    if error:
        raise error
    return result


def export_personal_data(service, profile, account):
    db = service.store.db
    player = service.store.profile(profile)
    def rows(sql, params=(profile,)):
        return [dict(row) for row in db.execute(sql, params)]
    history = []
    for row in db.execute('SELECT m.state_json,r.outcome FROM match_results r JOIN matches m ON m.id=r.match_id WHERE r.profile_id=?', (profile,)):
        match = json.loads(row['state_json'])
        history.append({key: match.get(key) for key in ('id', 'created', 'ended', 'stadium', 'score', 'source', 'mode')} | {'outcome': row['outcome']})
    activity = {row['day']: row for row in rows('SELECT day,first_seen,last_seen,requests,logins,reconnects,connection_gaps,online_seconds FROM tracking_activity WHERE profile_id=?')}
    with service.tracking.lock:
        for (day, owner), pending in service.tracking.activity_rows.items():
            if owner != profile:
                continue
            item = activity.setdefault(day, dict(day=day, first_seen=pending[0], last_seen=pending[1], requests=0, logins=0, reconnects=0, connection_gaps=0, online_seconds=0))
            item['first_seen'] = min(item['first_seen'], pending[0])
            item['last_seen'] = max(item['last_seen'], pending[1])
            for key, value in zip(('requests','logins','reconnects','connection_gaps','online_seconds'), pending[2:]):
                item[key] += value
    # Do not expose opponents' profiles, orders, reports, credentials or any replay/seed data.
    return {
        'format_version': 1, 'exported_at': time.time(),
        'identity': {'nickname': player['nickname'], 'username': account['username'] if account else None,
                     'authentication': 'account' if account else 'device',
                     'created': db.execute('SELECT created FROM profiles WHERE id=?', (profile,)).fetchone()[0]},
        'clubs': player['club'], 'statistics': player['statistics'], 'match_results': history,
        'sent_messages': rows('SELECT message,created,language,CASE WHEN recipient IS NOT NULL THEN \'direct\' WHEN match_id IS NOT NULL THEN \'match\' ELSE \'channel\' END AS audience FROM chat_messages WHERE sender=?'),
        'friends': rows('SELECT p.nickname,f.status,CASE WHEN f.requester=? THEN \'sent\' ELSE \'received\' END AS direction,f.created FROM friendships f JOIN profiles p ON p.id=CASE WHEN f.requester=? THEN f.target ELSE f.requester END WHERE f.requester=? OR f.target=?', (profile,) * 4),
        'blocked_players': rows('SELECT p.nickname,b.created FROM blocks b JOIN profiles p ON p.id=b.target WHERE b.owner=?'),
        'channels': rows('SELECT language FROM chat_subscriptions WHERE profile_id=?'),
        'tournaments': rows('SELECT tournament_id,joined FROM tournament_participants WHERE profile_id=?'),
        'tournament_rewards': rows('SELECT tournament_id,reward,awarded FROM tournament_rewards WHERE profile_id=?'),
        'cosmetics': rows('SELECT item_id,created FROM cosmetic_unlocks WHERE profile_id=?'),
        'purchases': rows('SELECT item_id,amount_json,created FROM economy_ledger WHERE profile_id=?'),
        'season_rankings': rows('SELECT season_id,statistics_json FROM season_rankings WHERE profile_id=?'),
        'activity': list(activity.values()),
        'reports_sent': rows('SELECT reason,created FROM reports WHERE reporter=?'),
        'session_expirations': rows('SELECT kind,expires FROM sessions WHERE profile_id=?'),
        'notice': 'Export personnel : les messages reçus, données privées des adversaires, secrets et replays sont exclus. Les statistiques techniques globales ne sont pas attribuables à un compte.'}


def delete_personal_data(service, profile):
    db = service.store.db
    old = service.store.profile(profile)
    nickname = old['nickname']
    anonymous = 'Supprimé-' + secrets.token_hex(8)
    tombstone = str(uuid.uuid4())
    # A non-login tombstone keeps foreign keys, classifications, brackets and results valid.
    from backend.cpu_team import default_cpu_club
    club = default_cpu_club()
    club['clubName'] = 'Club supprimé'
    statistics = dict(old['statistics'])
    statistics.pop('tournament_wallet', None)
    db.execute('INSERT INTO profiles VALUES(?,?,?,?,0)',
               (tombstone, anonymous, json.dumps({'active': club['clubId'], 'clubs': {club['clubId']: club}}), json.dumps(statistics)))
    service.leave_queue(profile)
    for offer in db.execute("SELECT * FROM challenges WHERE (host=? OR guest=?) AND status='pending'", (profile, profile)).fetchall():
        service.cancel_offer(offer)
    service.stop_spectating(profile)

    def scrub(value):
        if isinstance(value, list):
            return [scrub(child) for child in value]
        if not isinstance(value, dict):
            return anonymous if value == nickname else tombstone if value == profile else value
        value = dict(value)
        if value.get('nickname') == nickname:
            value['nickname'] = anonymous
            # Match rosters and cached player summaries contain editable personal names.
            if 'name' in value:
                value['name'] = 'Club supprimé'
            if 'characters' in value:
                value['characters'] = [dict(p, name='Joueur ' + str(i + 1)) for i, p in enumerate(value['characters'])]
            if 'club' in value:
                value['club'] = {**value['club'], 'clubName': 'Club supprimé'}
        if value.get('fromNickname') == nickname or value.get('from') == nickname:
            value['message'] = '[message supprimé]'
        if 'hex' in value and 'type' in value:
            codec = service.chat_codec if value.get('channel') == 'CHAT' else service.codec
            payload = codec.open_envelope(bytes.fromhex(value['hex']))['payload']
            cleaned = scrub(payload)
            if cleaned != payload:
                value['hex'] = codec.envelope(value['type'], cleaned).hex()
        return {tombstone if key == profile else key: scrub(child) for key, child in value.items()}

    for row in db.execute('SELECT id,state_json FROM matches WHERE id IN (SELECT match_id FROM participants WHERE profile_id=?)', (profile,)).fetchall():
        match = scrub(json.loads(row['state_json']))
        db.execute('UPDATE matches SET state_json=? WHERE id=?', (json.dumps(match), row['id']))
        for turn in db.execute('SELECT turn,record_json FROM turns WHERE match_id=?', (row['id'],)).fetchall():
            record = scrub(json.loads(turn['record_json']))
            db.execute('UPDATE turns SET record_json=? WHERE match_id=? AND turn=?', (json.dumps(record), row['id'], turn['turn']))
    # Cached protocol packets can contain old names and sent chat even after source rows vanish.
    for table, column in (('events', 'packet_json'), ('commands', 'response_json')):
        for row in db.execute(f'SELECT rowid AS privacy_rowid,{column} FROM {table} WHERE profile_id<>?', (profile,)).fetchall():
            original = json.loads(row[column])
            cleaned = scrub(original)
            if cleaned != original:
                db.execute(f'UPDATE {table} SET {column}=? WHERE rowid=?', (json.dumps(cleaned), row['privacy_rowid']))
    for row in db.execute('SELECT rowid AS privacy_rowid,eligible_json FROM tournament_rounds').fetchall():
        db.execute('UPDATE tournament_rounds SET eligible_json=? WHERE rowid=?', (json.dumps(scrub(json.loads(row['eligible_json']))), row['privacy_rowid']))
    for row in db.execute('SELECT id,final_entries_json FROM tournaments WHERE final_entries_json IS NOT NULL').fetchall():
        db.execute('UPDATE tournaments SET final_entries_json=? WHERE id=?', (json.dumps(scrub(json.loads(row['final_entries_json']))), row['id']))
    db.execute('DELETE FROM deleted_sessions WHERE expires<=?', (time.time(),))
    db.execute('INSERT OR REPLACE INTO deleted_sessions SELECT token_hash,expires FROM sessions WHERE profile_id=?', (profile,))
    for table in ('sessions', 'accounts', 'events', 'commands', 'presence', 'chat_subscriptions', 'replay_access',
                  'spectators', 'tournament_watchers', 'tournament_intentions', 'profile_roles', 'cosmetic_unlocks',
                  'economy_ledger', 'tracking_activity', 'tracking_visits', 'tracking_clients', 'tracking_receipts'):
        db.execute(f'DELETE FROM {table} WHERE profile_id=?', (profile,))
    for table, first, second in (('friendships', 'requester', 'target'), ('blocks', 'owner', 'target'),
                                  ('challenges', 'host', 'guest'), ('reports', 'reporter', 'target'),
                                  ('chat_messages', 'sender', 'recipient')):
        db.execute(f'DELETE FROM {table} WHERE {first}=? OR {second}=?', (profile, profile))
    # Retain moderation decisions affecting other people, remove free text tied to this identity.
    db.execute('DELETE FROM sanctions WHERE profile_id=?', (profile,))
    db.execute("UPDATE sanctions SET actor=NULL,reason='[acteur supprimé]' WHERE actor=?", (profile,))
    db.execute('DELETE FROM moderation_audit WHERE target=?', (profile,))
    db.execute("UPDATE moderation_audit SET actor=NULL,reason='[acteur supprimé]' WHERE actor=?", (profile,))
    db.execute("UPDATE admin_events SET details='{}' WHERE actor=?", (profile,))
    for table in ('participants', 'match_results', 'tournament_participants', 'season_rankings'):
        db.execute(f'UPDATE {table} SET profile_id=? WHERE profile_id=?', (tombstone, profile))
    db.execute('UPDATE admin_events SET actor=? WHERE actor=?', (tombstone, profile))
    db.execute('DELETE FROM tournament_rewards WHERE profile_id=?', (profile,))
    for row in db.execute('SELECT rowid AS privacy_rowid,statistics_json FROM season_rankings WHERE profile_id=?', (tombstone,)).fetchall():
        statistics = json.loads(row['statistics_json'])
        statistics.pop('tournament_wallet', None)
        db.execute('UPDATE season_rankings SET statistics_json=? WHERE rowid=?', (json.dumps(statistics), row['privacy_rowid']))
    db.execute('DELETE FROM profiles WHERE id=?', (profile,))
    # Tracking flush is buffered: remove memory as well as SQL rows, under its lock.
    tracker = service.tracking
    with tracker.lock:
        for name, index in (('activity_rows', 1), ('clients', 1), ('seen', 0), ('metadata', 0), ('rates', 0)):
            cache = getattr(tracker, name)
            for key in list(cache):
                if key[index] == profile:
                    del cache[key]
        tracker.profile_seen.pop(profile, None)
        for key, visit in list(tracker.visits.items()):
            if visit[1] == profile:
                del tracker.visits[key]
    service.store.pending_notifications.add(profile)
