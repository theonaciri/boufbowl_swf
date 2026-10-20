"""Buffered usage and diagnostic aggregates; independent of gameplay statistics."""
from collections import Counter
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading
import time
import uuid

BUCKETS = (1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000, 15000, 30000, 120000)
PLATFORMS = {'browser', 'android', 'linux', 'windows', 'macos', 'unknown'}
SITE_SECTIONS = {'hero', 'telecharger', 'le-jeu', 'le-chantier', 'vestiaires', 'benevoles', 'manifesto', 'final-cta'}
SITE_DOWNLOADS = {'desktop', 'windows', 'android'}
SITE_CLASSES = frozenset(row['class_name'] for row in json.loads(
    (Path(__file__).resolve().parent.parent / 'assets/site/restoration/inventory.json').read_text()
)['characters'] if not row.get('hero'))
SITE_CHARACTERS = frozenset(row['name'] for row in json.loads(
    (Path(__file__).resolve().parent.parent / 'assets/site/restoration/inventory.json').read_text()
)['characters'] if row.get('hero'))


def day_at(stamp):
    return datetime.fromtimestamp(stamp, timezone.utc).date().isoformat()


def init_schema(db):
    # Additive tables deliberately leave the game's schema version and data intact.
    db.executescript('''
        CREATE TABLE IF NOT EXISTS tracking_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tracking_activity(
          day TEXT NOT NULL,profile_id TEXT NOT NULL,first_seen REAL NOT NULL,last_seen REAL NOT NULL,
          requests INTEGER NOT NULL DEFAULT 0,logins INTEGER NOT NULL DEFAULT 0,
          reconnects INTEGER NOT NULL DEFAULT 0,connection_gaps INTEGER NOT NULL DEFAULT 0,
          online_seconds REAL NOT NULL DEFAULT 0,observed INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY(day,profile_id));
        CREATE INDEX IF NOT EXISTS tracking_activity_profile ON tracking_activity(profile_id,day);
        CREATE TABLE IF NOT EXISTS tracking_visits(
          id TEXT PRIMARY KEY,profile_id TEXT NOT NULL,client_id TEXT NOT NULL,
          started REAL NOT NULL,last_seen REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS tracking_visits_client ON tracking_visits(profile_id,client_id,last_seen);
        CREATE TABLE IF NOT EXISTS tracking_clients(
          day TEXT NOT NULL,profile_id TEXT NOT NULL,client_id TEXT NOT NULL,platform TEXT NOT NULL,
          metadata_json TEXT NOT NULL,updated REAL NOT NULL,PRIMARY KEY(day,profile_id,client_id));
        CREATE INDEX IF NOT EXISTS tracking_clients_profile ON tracking_clients(profile_id,client_id,day);
        CREATE INDEX IF NOT EXISTS tracking_matches_phase ON matches(json_extract(state_json,'$.phase'));
        CREATE INDEX IF NOT EXISTS tracking_matches_created ON matches(json_extract(state_json,'$.created'));
        CREATE INDEX IF NOT EXISTS tracking_matches_ended ON matches(json_extract(state_json,'$.ended'));
        CREATE TABLE IF NOT EXISTS tracking_performance(
          day TEXT NOT NULL,kind TEXT NOT NULL,name TEXT NOT NULL,count INTEGER NOT NULL,
          errors INTEGER NOT NULL,total_ms REAL NOT NULL,max_ms REAL NOT NULL,histogram_json TEXT NOT NULL,
          PRIMARY KEY(day,kind,name));
        CREATE TABLE IF NOT EXISTS tracking_errors(
          day TEXT NOT NULL,origin TEXT NOT NULL,code TEXT NOT NULL,fingerprint TEXT NOT NULL,
          message TEXT NOT NULL,stack TEXT NOT NULL,count INTEGER NOT NULL,last_seen REAL NOT NULL,
          PRIMARY KEY(day,origin,code,fingerprint));
        CREATE TABLE IF NOT EXISTS tracking_samples(
          minute INTEGER PRIMARY KEY,day TEXT NOT NULL,online INTEGER NOT NULL,
          active_matches INTEGER NOT NULL,queued INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS tracking_receipts(
          profile_id TEXT NOT NULL,client_id TEXT NOT NULL,event_id TEXT NOT NULL,created REAL NOT NULL,
          PRIMARY KEY(profile_id,client_id,event_id));
        CREATE INDEX IF NOT EXISTS tracking_receipts_age ON tracking_receipts(created);
        CREATE INDEX IF NOT EXISTS tracking_receipts_client ON tracking_receipts(profile_id,client_id,created);
        CREATE TABLE IF NOT EXISTS website_analytics(
          day TEXT NOT NULL,kind TEXT NOT NULL,name TEXT NOT NULL,count INTEGER NOT NULL DEFAULT 0,
          duration_seconds REAL NOT NULL DEFAULT 0,PRIMARY KEY(day,kind,name));
        CREATE INDEX IF NOT EXISTS website_analytics_day ON website_analytics(day,kind);
    ''')


def backfill(store):
    """Recover only activity evidenced by old records, never inferred logins/peaks."""
    db = store.db
    if db.execute("SELECT 1 FROM tracking_meta WHERE key='backfill_v1'").fetchone():
        return
    db.execute('''INSERT INTO tracking_activity(day,profile_id,first_seen,last_seen)
        SELECT strftime('%Y-%m-%d',stamp,'unixepoch'),profile_id,MIN(stamp),MAX(stamp) FROM (
          SELECT id AS profile_id,created AS stamp FROM profiles
          UNION ALL SELECT profile_id,created FROM accounts
          UNION ALL SELECT sender,created FROM chat_messages
          UNION ALL SELECT profile_id,seen FROM presence
          UNION ALL SELECT p.profile_id,json_extract(m.state_json,'$.created') FROM participants p
            JOIN matches m ON m.id=p.match_id WHERE p.profile_id IS NOT NULL
        ) WHERE stamp>0 GROUP BY 1,2
        ON CONFLICT(day,profile_id) DO UPDATE SET first_seen=MIN(first_seen,excluded.first_seen),
          last_seen=MAX(last_seen,excluded.last_seen)''')
    db.execute("INSERT INTO tracking_meta VALUES('backfill_v1',?)", (str(time.time()),))


def clean_text(value, limit=400):
    value = str(value or '')[:limit * 2]
    value = re.sub(r'https?://[^\s]+', lambda m: m[0].split('?')[0].split('#')[0], value)
    value = re.sub(r'(?i)(password|session|token|authorization|recovery_code)([\s:=]+)[^\s,;]+', r'\1\2[redacted]', value)
    value = re.sub(r'[A-Za-z0-9_\-]{32,}', '[redacted]', value)
    return ''.join(c for c in value if c in '\n\t' or ord(c) >= 32)[:limit]


def client_metadata(raw):
    raw = raw if isinstance(raw, dict) else {}
    platform = raw.get('platform', 'unknown')
    result = {'platform': platform if isinstance(platform, str) and platform in PLATFORMS else 'unknown'}
    for name in ('runtime', 'game_version', 'runtime_version', 'host_os', 'reported_os', 'cpu', 'language', 'browser', 'client_build'):
        result[name] = clean_text(raw.get(name), 120)
    build = raw.get('client_build')
    if isinstance(build, str) and re.fullmatch(r'[a-fA-F0-9]{64}', build):
        result['client_build'] = build
    for name in ('screen_width', 'screen_height'):
        value = raw.get(name)
        result[name] = value if type(value) is int and 0 <= value <= 32768 else None
    for name in ('gpu', 'debugger'):
        result[name] = raw.get(name) if type(raw.get(name)) is bool else None
    return result


def client_id(body):
    value = body.get('client_id')
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value) else 'legacy'


class Tracking:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self.activity_rows = {}
        self.visits = {}
        self.clients = {}
        self.performance = {}
        self.errors = {}
        self.samples = {}
        self.website_rows = {}
        self.seen = {}
        self.profile_seen = {}
        self.metadata = {}
        self.rates = {}
        self.started = time.monotonic()
        self.last_flush = self.started
        with store.transaction():
            store.db.execute("INSERT OR IGNORE INTO tracking_meta VALUES('started_at',?)", (str(time.time()),))
            backfill(store)

    def activity(self, profile, body, login=False):
        now = time.time()
        day, device = day_at(now), client_id(body)
        key = (profile, device)
        with self.lock:
            previous = self.seen.get(key)
            if previous is None:
                row = self.store.db.execute('SELECT id,started,last_seen FROM tracking_visits WHERE profile_id=? AND client_id=? ORDER BY last_seen DESC LIMIT 1', key).fetchone()
                previous = (row['id'], row['started'], row['last_seen']) if row else None
            if previous and 0 <= now - previous[2] <= 90:
                visit = (previous[0], previous[1], now)
            else:
                visit = (uuid.uuid4().hex, now, now)
            self.seen[key] = visit
            self.visits[visit[0]] = (visit[0], profile, device, visit[1], now)
            row = self.activity_rows.setdefault((day, profile), [now, now, 0, 0, 0, 0, 0.0])
            row[1] = max(row[1], now)
            row[2] += 1
            row[3] += int(login)
            if previous and now - previous[2] > 30:
                row[5] += 1
            last = self.profile_seen.get(profile)
            if last is not None and 0 < now - last <= 90:
                # Split estimated online time across UTC midnight. Concurrent
                # devices contribute once per profile, not once per connection.
                cursor = last
                while cursor < now:
                    boundary = (math.floor(cursor / 86400) + 1) * 86400
                    end = min(now, boundary)
                    interval = self.activity_rows.setdefault((day_at(cursor), profile), [cursor, end, 0, 0, 0, 0, 0.0])
                    interval[6] += end - cursor
                    interval[1] = max(interval[1], end)
                    cursor = end
            self.profile_seen[profile] = max(last or now, now)
            if login or key not in self.metadata:
                raw = body.get('client')
                if raw is None:
                    old = self.store.db.execute('SELECT metadata_json FROM tracking_clients WHERE profile_id=? AND client_id=? ORDER BY day DESC LIMIT 1', key).fetchone()
                    raw = json.loads(old[0]) if old else None
                self.metadata[key] = client_metadata(raw)
            self.clients[(day, profile, device)] = self.metadata[key]
            # Inactive device caches are dispensable; durable visits restore on demand.
            if len(self.seen) > 10000:
                for old_key, old in list(self.seen.items()):
                    if now - old[2] > 90:
                        self.seen.pop(old_key, None)
                        self.metadata.pop(old_key, None)
                self.profile_seen = {p: stamp for p, stamp in self.profile_seen.items() if now - stamp <= 90}

    def observe(self, kind, name, elapsed_ms, error=False):
        now = time.time()
        if not isinstance(elapsed_ms, (int, float)) or not math.isfinite(elapsed_ms):
            return
        value = max(0.0, min(float(elapsed_ms), 3600000))
        with self.lock:
            row = self.performance.setdefault((day_at(now), kind, name), [0, 0, 0.0, 0.0, [0] * len(BUCKETS)])
            row[0] += 1
            row[1] += int(error)
            row[2] += value
            row[3] = max(row[3], value)
            bucket = next((i for i, bound in enumerate(BUCKETS) if value <= bound), len(BUCKETS) - 1)
            row[4][bucket] += 1

    def website_asset_request(self, path):
        path = str(path or '').lstrip('/')
        if (not path.startswith('assets/') or len(path) > 240 or '..' in path.split('/')
                or '\\' in path or any(ord(char) < 32 for char in path)):
            return
        self._website_event('asset_request', path)

    def website_events(self, body):
        events = body.get('events')
        if not isinstance(events, list) or not 1 <= len(events) <= 40:
            raise ValueError('Send between one and forty website events')
        accepted = []
        for event in events:
            if not isinstance(event, dict):
                raise ValueError('Website events must be objects')
            kind, name = event.get('kind'), event.get('name')
            if not isinstance(name, str):
                raise ValueError('Website event name is required')
            allowed = {
                'section_view': SITE_SECTIONS,
                'section_time': SITE_SECTIONS,
                'class_interest': SITE_CLASSES,
                'character_interest': SITE_CHARACTERS,
                'download_click': SITE_DOWNLOADS,
                'web_click': {'play'},
            }.get(kind)
            if allowed is None or name not in allowed:
                raise ValueError('Unknown website event')
            duration = event.get('duration_ms', 0) if kind == 'section_time' else 0
            if type(duration) not in (int, float) or not math.isfinite(duration) or not 0 <= duration <= 3600000:
                raise ValueError('Invalid section duration')
            accepted.append((kind, name, duration / 1000.0))
        for kind, name, duration in accepted:
            self._website_event(kind, name, duration)
        return {'ok': True, 'accepted': len(accepted)}

    def _website_event(self, kind, name, duration=0.0):
        key = (day_at(time.time()), kind, name)
        with self.lock:
            row = self.website_rows.setdefault(key, [0, 0.0])
            row[0] += 1
            row[1] += duration

    def error(self, origin, code, message='', stack=''):
        now = time.time()
        code = clean_text(code, 80) or 'UNKNOWN'
        message, stack = clean_text(message), clean_text(stack, 2000)
        fingerprint = hashlib.sha256((message + '\n' + stack).encode()).hexdigest()[:20]
        with self.lock:
            key = (day_at(now), origin, code, fingerprint)
            if len(self.errors) >= 1000 and key not in self.errors:
                key = (day_at(now), origin, 'OTHER', 'overflow')
                message, stack = 'Additional distinct errors', ''
            row = self.errors.setdefault(key, [message, stack, 0, now])
            row[2] += 1
            row[3] = now

    def telemetry(self, profile, body):
        events = body.get('events')
        if not isinstance(events, list) or len(events) > 20:
            raise ValueError('Send at most twenty diagnostic events')
        now, device = time.time(), client_id(body)
        accepted = duplicates = limited = 0
        # Caller owns a transaction; receipts make reconnect retries idempotent.
        for event in events:
            if not isinstance(event, dict) or event.get('kind') not in ('error', 'reconnect', 'latency'):
                raise ValueError('Unknown diagnostic event')
            identity = event.get('id')
            if not isinstance(identity, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', identity):
                raise ValueError('Diagnostic events need an ID')
        with self.lock:
            window, count = self.rates.get((profile, device), (now, 0))
            if now - window >= 60:
                window, count = now, 0
            for event in events:
                if self.store.db.execute('SELECT 1 FROM tracking_receipts WHERE profile_id=? AND client_id=? AND event_id=?', (profile, device, event['id'])).fetchone():
                    duplicates += 1
                    continue
                if count >= 60:
                    limited += 1
                    continue
                self.store.db.execute('INSERT INTO tracking_receipts VALUES(?,?,?,?)', (profile, device, event['id'], now))
                count += 1
                accepted += 1
                if event['kind'] == 'error':
                    self.error('client', event.get('code', 'RUNTIME_ERROR'), event.get('message'), event.get('stack'))
                elif event['kind'] == 'reconnect':
                    row = self.activity_rows.setdefault((day_at(now), profile), [now, now, 0, 0, 0, 0, 0.0])
                    row[4] += 1
                    downtime = event.get('downtime_ms', 0)
                    if type(downtime) in (int, float) and math.isfinite(downtime):
                        self.observe('connection', 'recovery', downtime)
                elif event.get('route') in ('hello', 'command', 'community', 'account', 'replay'):
                    elapsed = event.get('elapsed_ms')
                    if type(elapsed) in (int, float) and math.isfinite(elapsed):
                        self.observe('client_latency', event['route'], elapsed)
            self.rates[(profile, device)] = (window, count)
            # The client buffers at most 32 events and sends one batch at a time.
            # Keep a bounded retry window instead of a raw event log per sample.
            self.store.db.execute('''DELETE FROM tracking_receipts WHERE profile_id=? AND client_id=? AND rowid NOT IN
              (SELECT rowid FROM tracking_receipts WHERE profile_id=? AND client_id=? ORDER BY created DESC,rowid DESC LIMIT 128)''',
                                  (profile, device, profile, device))
        return {'ok': True, 'accepted': accepted, 'duplicates': duplicates, 'limited': limited}

    def sample(self):
        now = time.time()
        with self.store.lock:
            online = self.store.db.execute('SELECT COUNT(*) FROM presence WHERE seen>?', (now - 90,)).fetchone()[0]
            matches = self.store.db.execute("SELECT COUNT(*) FROM matches WHERE json_extract(state_json,'$.phase')!='ended'").fetchone()[0]
            queued = self.store.db.execute('SELECT COUNT(*) FROM matchmaking_queue').fetchone()[0]
        with self.lock:
            key = int(now // 60)
            old = self.samples.get(key, (day_at(now), 0, 0, 0))
            self.samples[key] = (day_at(now), max(old[1], online), max(old[2], matches), max(old[3], queued))

    def flush(self, force=False):
        if not force and time.monotonic() - self.last_flush < 60:
            return
        # One separate transaction per flush, never a write on every poll.
        with self.store.lock, self.lock:
            db = self.store.db
            with self.store.transaction():
                for (day, profile), row in self.activity_rows.items():
                    db.execute('''INSERT INTO tracking_activity VALUES(?,?,?,?,?,?,?,?,?,1)
                      ON CONFLICT(day,profile_id) DO UPDATE SET first_seen=MIN(first_seen,excluded.first_seen),
                      last_seen=MAX(last_seen,excluded.last_seen),requests=requests+excluded.requests,
                      logins=logins+excluded.logins,reconnects=reconnects+excluded.reconnects,
                      connection_gaps=connection_gaps+excluded.connection_gaps,
                      online_seconds=online_seconds+excluded.online_seconds,observed=1''', (day, profile, *row))
                db.executemany('''INSERT INTO tracking_visits VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET last_seen=MAX(last_seen,excluded.last_seen)''', self.visits.values())
                for (day, profile, device), metadata in self.clients.items():
                    db.execute('''INSERT INTO tracking_clients VALUES(?,?,?,?,?,?) ON CONFLICT(day,profile_id,client_id)
                      DO UPDATE SET platform=excluded.platform,metadata_json=excluded.metadata_json,updated=excluded.updated''',
                               (day, profile, device, metadata['platform'], json.dumps(metadata), time.time()))
                for key, row in self.performance.items():
                    old = db.execute('SELECT * FROM tracking_performance WHERE day=? AND kind=? AND name=?', key).fetchone()
                    histogram = row[4] if not old else [a + b for a, b in zip(row[4], json.loads(old['histogram_json']))]
                    db.execute('INSERT OR REPLACE INTO tracking_performance VALUES(?,?,?,?,?,?,?,?)',
                               (*key, row[0] + (old['count'] if old else 0), row[1] + (old['errors'] if old else 0),
                                row[2] + (old['total_ms'] if old else 0), max(row[3], old['max_ms'] if old else 0), json.dumps(histogram)))
                for key, row in self.errors.items():
                    db.execute('''INSERT INTO tracking_errors VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(day,origin,code,fingerprint)
                      DO UPDATE SET count=count+excluded.count,last_seen=MAX(last_seen,excluded.last_seen)''', (*key, *row))
                for minute, row in self.samples.items():
                    db.execute('''INSERT INTO tracking_samples VALUES(?,?,?,?,?) ON CONFLICT(minute) DO UPDATE SET
                      online=MAX(online,excluded.online),active_matches=MAX(active_matches,excluded.active_matches),queued=MAX(queued,excluded.queued)''', (minute, *row))
                for (day, kind, name), row in self.website_rows.items():
                    db.execute('''INSERT INTO website_analytics VALUES(?,?,?,?,?) ON CONFLICT(day,kind,name) DO UPDATE SET
                      count=count+excluded.count,duration_seconds=duration_seconds+excluded.duration_seconds''',
                               (day, kind, name, *row))
                db.execute("INSERT OR REPLACE INTO tracking_meta VALUES('runtime',?)", (json.dumps(self.resources()),))
                db.execute('DELETE FROM tracking_receipts WHERE created<?', (time.time() - 7 * 86400,))
                db.execute('DELETE FROM website_analytics WHERE day<?', (day_at(time.time() - 400 * 86400),))
            self.activity_rows.clear(); self.visits.clear(); self.clients.clear()
            self.performance.clear(); self.errors.clear(); self.samples.clear()
            self.website_rows.clear()
            self.last_flush = time.monotonic()
            now = time.time()
            self.rates = {key: value for key, value in self.rates.items() if now - value[0] < 60}

    def resources(self):
        def rss(pid):
            try:
                with open(f'/proc/{pid}/statm') as stream:
                    return int(stream.read().split()[1]) * os.sysconf('SC_PAGE_SIZE') / 1048576
            except (OSError, ValueError, IndexError):
                return None
        engine = getattr(self, 'engine', None)
        process = getattr(engine, 'process', None)
        return {'sampled_at': time.time(), 'uptime_seconds': time.monotonic() - self.started, 'python_cpu_seconds': time.process_time(),
                'python_rss_mb': rss(os.getpid()), 'simulator_rss_mb': rss(process.pid) if process else None}


def metrics_report(store, days=30):
    if type(days) is not int or not 1 <= days <= 365:
        raise ValueError('Choose between one and 365 days')
    now = time.time()
    today = datetime.fromtimestamp(now, timezone.utc).date()
    start = today - timedelta(days=days - 1)
    since = datetime.combine(start, datetime.min.time(), timezone.utc).timestamp()
    db = store.db
    meta = dict(db.execute('SELECT key,value FROM tracking_meta').fetchall())
    daily = {str(start + timedelta(days=i)): {'day': str(start + timedelta(days=i)), 'active_users': 0,
             'returning_users': 0, 'new_profiles': 0, 'new_accounts': 0, 'requests': 0, 'logins': 0,
             'reconnects': 0, 'connection_gaps': 0, 'online_seconds': None, 'peak_online': None,
             'matches_started': 0, 'matches_completed': 0, 'chat_messages': 0} for i in range(days)}
    activity = db.execute('''SELECT a.*, (SELECT MIN(day) FROM tracking_activity first WHERE first.profile_id=a.profile_id) AS first_day
        FROM tracking_activity a WHERE day>=? ORDER BY day''', (str(start),)).fetchall()
    active, returning = set(), set()
    for row in activity:
        if row['day'] not in daily:
            continue
        item = daily[row['day']]
        active.add(row['profile_id']); item['active_users'] += 1
        if row['first_day'] < row['day']:
            item['returning_users'] += 1
            returning.add(row['profile_id'])
        for name in ('requests', 'logins', 'reconnects', 'connection_gaps'):
            item[name] += row[name]
        if row['observed']:
            item['online_seconds'] = (item['online_seconds'] or 0) + row['online_seconds']
    for table, column, metric in (('profiles', 'created', 'new_profiles'), ('accounts', 'created', 'new_accounts'), ('chat_messages', 'created', 'chat_messages')):
        for row in db.execute(f"SELECT strftime('%Y-%m-%d',{column},'unixepoch') AS day,COUNT(*) AS n FROM {table} WHERE {column}>=? GROUP BY day", (since,)):
            if row['day'] in daily:
                daily[row['day']][metric] = row['n']
    peak = None
    for row in db.execute('SELECT day,MAX(online) AS peak FROM tracking_samples WHERE day>=? GROUP BY day', (str(start),)):
        if row['day'] in daily:
            daily[row['day']]['peak_online'] = row['peak']
            peak = max(peak or 0, row['peak'])
    matches = {'started': 0, 'completed': 0, 'surrendered': 0, 'cpu': 0, 'human': 0}
    durations, turn_counts, stadiums = [], [], Counter()
    for row in db.execute('''SELECT m.state_json,(SELECT COUNT(*) FROM turns t WHERE t.match_id=m.id) AS turns
         FROM matches m WHERE json_extract(state_json,'$.created')>=? OR json_extract(state_json,'$.ended')>=?''', (since, since)):
        match = json.loads(row['state_json'])
        created, ended = match.get('created', 0), match.get('ended', 0)
        if since <= created <= now:
            matches['started'] += 1
            matches['human' if all(match.get('profiles', [])) else 'cpu'] += 1
            stadiums[match.get('stadium', 'unknown')] += 1
            daily[day_at(created)]['matches_started'] += 1
        if match.get('phase') == 'ended' and since <= ended <= now:
            matches['completed'] += 1
            matches['surrendered'] += int(match.get('given_up') is not None)
            durations.append(max(0, ended - created)); turn_counts.append(row['turns'])
            daily[day_at(ended)]['matches_completed'] += 1
    matches['mean_duration_seconds'] = sum(durations) / len(durations) if durations else None
    matches['mean_turns'] = sum(turn_counts) / len(turn_counts) if turn_counts else None
    from tools.game_config import STADIUMS
    matches['stadiums'] = [{'stadium': key, 'name': STADIUMS[key - 1] if type(key) is int and 1 <= key <= len(STADIUMS) else 'Unknown',
                           'matches': count} for key, count in stadiums.most_common()]
    performance = {}
    for row in db.execute('SELECT * FROM tracking_performance WHERE day>=?', (str(start),)):
        key = (row['kind'], row['name'])
        item = performance.setdefault(key, {'kind': key[0], 'name': key[1], 'count': 0, 'errors': 0, 'total_ms': 0, 'max_ms': 0, 'histogram': [0] * len(BUCKETS)})
        for name in ('count', 'errors', 'total_ms'):
            item[name] += row[name]
        item['max_ms'] = max(item['max_ms'], row['max_ms'])
        item['histogram'] = [a + b for a, b in zip(item['histogram'], json.loads(row['histogram_json']))]
    for item in performance.values():
        item['mean_ms'] = item.pop('total_ms') / item['count']
        cumulative, target = 0, math.ceil(item['count'] * .95)
        for bound, n in zip(BUCKETS, item.pop('histogram')):
            cumulative += n
            if cumulative >= target:
                item['p95_bucket_ms'] = bound if item['max_ms'] <= BUCKETS[-1] else None
                break
    visits = db.execute('SELECT COUNT(*),AVG(last_seen-started) FROM tracking_visits WHERE last_seen>=?', (since,)).fetchone()
    platforms = [dict(r) for r in db.execute('SELECT platform,COUNT(DISTINCT profile_id) AS users,COUNT(DISTINCT client_id || profile_id) AS clients FROM tracking_clients WHERE day>=? GROUP BY platform ORDER BY users DESC', (str(start),))]
    versions = [dict(r) for r in db.execute("SELECT json_extract(metadata_json,'$.game_version') AS game_version,json_extract(metadata_json,'$.runtime') AS runtime,json_extract(metadata_json,'$.runtime_version') AS runtime_version,COUNT(DISTINCT profile_id) AS users FROM tracking_clients WHERE day>=? GROUP BY 1,2,3 ORDER BY users DESC", (str(start),))]
    diagnostics = []
    for row in db.execute('''SELECT c.*,p.nickname FROM tracking_clients c JOIN profiles p ON p.id=c.profile_id
        WHERE c.day>=? AND c.day=(SELECT MAX(day) FROM tracking_clients c2 WHERE c2.profile_id=c.profile_id AND c2.client_id=c.client_id)
        ORDER BY c.updated DESC LIMIT 50''', (str(start),)):
        diagnostics.append({'nickname': row['nickname'], 'updated': row['updated'], **json.loads(row['metadata_json'])})
    errors = [dict(r) for r in db.execute('''SELECT origin,code,message,stack,SUM(count) AS count,MAX(last_seen) AS last_seen FROM tracking_errors
        WHERE day>=? GROUP BY origin,code,fingerprint ORDER BY last_seen DESC LIMIT 50''', (str(start),))]
    totals = {name: db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for name, table in
              (('profiles', 'profiles'), ('accounts', 'accounts'), ('matches', 'matches'), ('turns', 'turns'), ('chat_messages', 'chat_messages'))}
    return {'ok': True, 'generated_at': now, 'period': {'days': days, 'since': since, 'timezone': 'UTC'},
            'coverage': {'started_at': float(meta['started_at']) if 'started_at' in meta else None,
                         'history': 'Earlier activity is partial: recovered from registrations, sent chat, match starts and last presence. Earlier peaks, sessions, errors and platform data are unavailable.',
                         'online': 'Online uses the existing 90-second grace period. Peaks are sampled once per second.',
                         'duration': 'Online time and visit duration are estimates from requests; they include short outages and do not measure focused play.',
                         'latency': 'HTTP poll latency includes intentional long-poll waiting. Client latency samples successful non-poll round trips, including network time, at most once per 30 seconds per client. p95 values are histogram upper bounds.'},
            'totals': totals, 'online': db.execute('SELECT COUNT(*) FROM presence WHERE seen>?', (now - 90,)).fetchone()[0],
            'active_matches': db.execute("SELECT COUNT(*) FROM matches WHERE json_extract(state_json,'$.phase')!='ended'").fetchone()[0],
            'queued': db.execute('SELECT COUNT(*) FROM matchmaking_queue').fetchone()[0], 'peak_online': peak,
            'usage': {'active_users': len(active), 'returning_users': len(returning), 'visits': visits[0],
                      'mean_visit_seconds': visits[1], 'estimated_online_seconds': sum(d['online_seconds'] or 0 for d in daily.values())},
            'daily': list(daily.values()), 'matches': matches, 'platforms': platforms, 'versions': versions,
            'diagnostics': diagnostics, 'performance': list(performance.values()), 'errors': errors,
            'resources': json.loads(meta['runtime']) if 'runtime' in meta else None}


def website_metrics_report(store, days=30):
    if type(days) is not int or not 1 <= days <= 365:
        raise ValueError('Choose between one and 365 days')
    now = time.time()
    today = datetime.fromtimestamp(now, timezone.utc).date()
    start = (today - timedelta(days=days - 1)).isoformat()
    rows = [dict(row) for row in store.db.execute('''SELECT kind,name,SUM(count) AS count,
        ROUND(SUM(duration_seconds),1) AS duration_seconds FROM website_analytics WHERE day>=?
        GROUP BY kind,name ORDER BY count DESC,name''', (start,))]
    by_kind = {}
    for kind in ('section_view', 'section_time', 'class_interest', 'character_interest',
                 'download_click', 'web_click', 'asset_request'):
        by_kind[kind] = [row for row in rows if row['kind'] == kind]
    sections = {}
    for row in by_kind['section_view']:
        sections[row['name']] = {'name': row['name'], 'views': row['count'], 'seconds': 0.0}
    for row in by_kind['section_time']:
        section = sections.setdefault(row['name'], {'name': row['name'], 'views': 0, 'seconds': 0.0})
        section['seconds'] = row['duration_seconds'] or 0.0
    sections = sorted(sections.values(), key=lambda row: (-row['views'], -row['seconds'], row['name']))
    return {'ok': True, 'generated_at': now, 'period': {'days': days, 'since': start, 'timezone': 'UTC'},
            'coverage': 'Aggregate events only; no visitor or client identifier is stored. Asset requests are server-observed; browser-cached assets do not generate a request.',
            'sections': sections, 'classes': by_kind['class_interest'], 'characters': by_kind['character_interest'],
            'downloads': by_kind['download_click'], 'web': by_kind['web_click'],
            'asset_requests': by_kind['asset_request'][:100]}
