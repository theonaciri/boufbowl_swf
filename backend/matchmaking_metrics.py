"""Anonymous, daily aggregates of completed queue searches."""
from datetime import datetime, timedelta, timezone
import math
import time

BUCKETS = (5, 15, 30, 60, 120, 300, 600, 1800, 3600)
RETENTION_DAYS = 400


def init_schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS matchmaking_exit_metrics(
        day TEXT NOT NULL, kind TEXT NOT NULL, outcome TEXT NOT NULL, bucket INTEGER NOT NULL,
        count INTEGER NOT NULL, duration_sum REAL NOT NULL,
        PRIMARY KEY(day,kind,outcome,bucket))''')
    db.execute("INSERT OR IGNORE INTO tracking_meta VALUES('matchmaking_metrics_started_at',?)", (str(time.time()),))
    db.execute('DELETE FROM matchmaking_exit_metrics WHERE day<?',
               (str(datetime.now(timezone.utc).date() - timedelta(days=RETENTION_DAYS)),))


def record(db, entry, outcome, ended):
    duration = max(0, ended - entry['joined'])
    bucket = next((limit for limit in BUCKETS if duration <= limit), 0)
    day = datetime.fromtimestamp(ended, timezone.utc).date()
    kind = 'tournament' if entry['tournament_id'] is not None else 'regular'
    db.execute('''INSERT INTO matchmaking_exit_metrics VALUES(?,?,?,?,1,?)
        ON CONFLICT(day,kind,outcome,bucket) DO UPDATE SET
        count=count+1,duration_sum=duration_sum+excluded.duration_sum''',
        (str(day), kind, outcome, bucket, duration))
    db.execute('DELETE FROM matchmaking_exit_metrics WHERE day<?', (str(day - timedelta(days=RETENTION_DAYS)),))


def report(db, start_day):
    grouped = {}
    for row in db.execute('SELECT * FROM matchmaking_exit_metrics WHERE day>=? ORDER BY day,kind,outcome', (start_day,)):
        key = (row['day'], row['kind'], row['outcome'])
        group = grouped.setdefault(key, {'day':key[0], 'kind':key[1], 'outcome':key[2], 'count':0, 'duration_sum':0, 'buckets':{}})
        group['count'] += row['count']; group['duration_sum'] += row['duration_sum']
        group['buckets'][row['bucket']] = row['count']
    rows = []
    for group in grouped.values():
        def percentile(fraction):
            target = math.ceil(group['count'] * fraction); cumulative = 0
            for bound in (*BUCKETS, 0):
                cumulative += group['buckets'].get(bound, 0)
                if cumulative >= target: return bound or None
        group['mean_seconds'] = group.pop('duration_sum') / group['count']
        group['p50_upper_seconds'] = percentile(.5)
        group['p95_upper_seconds'] = percentile(.95)
        del group['buckets']
        rows.append(group)
    started = db.execute("SELECT value FROM tracking_meta WHERE key='matchmaking_metrics_started_at'").fetchone()
    return {'coverage_started_at': float(started[0]), 'rows': rows}
