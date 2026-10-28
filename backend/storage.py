"""SQLite state, authenticated device sessions, ordered delivery and retry safety."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import threading
import time
import uuid
from backend.results import POLICY_VERSION, result_kind, fresh_statistics, credit


class ServiceError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


class Store:
    def __init__(self, path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.waiters = {}
        self.pending_notifications = set()
        self.commit_callbacks = []
        self.closed = False
        self.db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        exists = self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_versions'").fetchone()
        version = self.db.execute('SELECT MAX(version) FROM schema_versions').fetchone()[0] if exists else None
        if version != 8:
            # Development databases are disposable; no historical migration/archive.
            self.db.execute('PRAGMA foreign_keys=OFF')
            tables = self.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
            for row in tables:
                self.db.execute('DROP TABLE "'+row[0].replace('"','""')+'"')
            self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript("""
            PRAGMA foreign_keys=ON;
            PRAGMA journal_mode=WAL;
            PRAGMA busy_timeout=10000;
            CREATE TABLE IF NOT EXISTS schema_versions(version INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS profiles(
              id TEXT PRIMARY KEY, nickname TEXT NOT NULL COLLATE NOCASE UNIQUE,
              club_json TEXT NOT NULL, statistics_json TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(
              token_hash TEXT PRIMARY KEY, profile_id TEXT NOT NULL REFERENCES profiles(id), expires REAL NOT NULL, kind TEXT NOT NULL DEFAULT 'device');
            CREATE TABLE IF NOT EXISTS deleted_sessions(
              token_hash TEXT PRIMARY KEY, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS matches(
              id INTEGER PRIMARY KEY AUTOINCREMENT, state_json TEXT NOT NULL, updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS participants(
              match_id INTEGER NOT NULL REFERENCES matches(id), side INTEGER NOT NULL CHECK(side IN (1,2)),
              profile_id TEXT REFERENCES profiles(id), PRIMARY KEY(match_id,side));
            CREATE TABLE IF NOT EXISTS events(
              seq INTEGER PRIMARY KEY AUTOINCREMENT, profile_id TEXT NOT NULL REFERENCES profiles(id),
              packet_json TEXT NOT NULL, created REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS events_by_profile ON events(profile_id,seq);
            CREATE TABLE IF NOT EXISTS commands(
              profile_id TEXT NOT NULL REFERENCES profiles(id), request_id TEXT NOT NULL,
              request_hash TEXT NOT NULL, response_json TEXT NOT NULL, PRIMARY KEY(profile_id,request_id));
            CREATE TABLE IF NOT EXISTS match_results(
              match_id INTEGER NOT NULL REFERENCES matches(id), profile_id TEXT NOT NULL REFERENCES profiles(id),
              outcome TEXT NOT NULL, PRIMARY KEY(match_id,profile_id));
            CREATE TABLE IF NOT EXISTS turns(
              match_id INTEGER NOT NULL REFERENCES matches(id), turn INTEGER NOT NULL,
              record_json TEXT NOT NULL, PRIMARY KEY(match_id,turn));
            CREATE TABLE IF NOT EXISTS challenges(
              id INTEGER PRIMARY KEY AUTOINCREMENT, host TEXT NOT NULL REFERENCES profiles(id),
              guest TEXT NOT NULL REFERENCES profiles(id), stadium INTEGER NOT NULL,
              status TEXT NOT NULL, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS chat_messages(
              id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT NOT NULL REFERENCES profiles(id),
              recipient TEXT REFERENCES profiles(id), match_id INTEGER REFERENCES matches(id),
              message TEXT NOT NULL, created REAL NOT NULL, language TEXT);
            CREATE TABLE IF NOT EXISTS spectators(
              profile_id TEXT PRIMARY KEY REFERENCES profiles(id),
              match_id INTEGER NOT NULL REFERENCES matches(id));


            CREATE TABLE IF NOT EXISTS accounts(
              username TEXT PRIMARY KEY COLLATE NOCASE,
              profile_id TEXT NOT NULL UNIQUE REFERENCES profiles(id),
              salt TEXT NOT NULL, password_hash TEXT NOT NULL, iterations INTEGER NOT NULL,
              created REAL NOT NULL, recovery_hash TEXT);
            CREATE TABLE IF NOT EXISTS auth_attempts(
              bucket TEXT PRIMARY KEY, failures INTEGER NOT NULL, reset_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS matchmaking_queue(
              profile_id TEXT PRIMARY KEY REFERENCES profiles(id), stadiums_json TEXT NOT NULL,
              joined REAL NOT NULL, heartbeat REAL NOT NULL, tournament_id TEXT);


            CREATE TABLE IF NOT EXISTS presence(
              profile_id TEXT PRIMARY KEY REFERENCES profiles(id), seen REAL NOT NULL,
              language TEXT NOT NULL DEFAULT 'en');
            CREATE TABLE IF NOT EXISTS friendships(
              requester TEXT NOT NULL REFERENCES profiles(id), target TEXT NOT NULL REFERENCES profiles(id),
              status TEXT NOT NULL CHECK(status IN ('pending','accepted')), created REAL NOT NULL,
              PRIMARY KEY(requester,target), CHECK(requester<>target));
            CREATE TABLE IF NOT EXISTS blocks(
              owner TEXT NOT NULL REFERENCES profiles(id), target TEXT NOT NULL REFERENCES profiles(id),
              created REAL NOT NULL, PRIMARY KEY(owner,target), CHECK(owner<>target));
            CREATE TABLE IF NOT EXISTS chat_subscriptions(
              profile_id TEXT NOT NULL REFERENCES profiles(id), language TEXT NOT NULL,
              PRIMARY KEY(profile_id,language));
            CREATE TABLE IF NOT EXISTS replay_access(
              profile_id TEXT NOT NULL REFERENCES profiles(id), match_id INTEGER NOT NULL REFERENCES matches(id),
              PRIMARY KEY(profile_id,match_id));

            CREATE TABLE IF NOT EXISTS reports(
              id INTEGER PRIMARY KEY AUTOINCREMENT, reporter TEXT NOT NULL REFERENCES profiles(id),
              target TEXT NOT NULL REFERENCES profiles(id), reason TEXT NOT NULL, created REAL NOT NULL);

            CREATE TABLE IF NOT EXISTS tournaments(
              id INTEGER PRIMARY KEY, settings_json TEXT NOT NULL, phase TEXT NOT NULL,
              final_entries_json TEXT, finalized REAL);
            CREATE TABLE IF NOT EXISTS tournament_participants(
              tournament_id INTEGER NOT NULL REFERENCES tournaments(id),
              profile_id TEXT NOT NULL REFERENCES profiles(id), joined REAL NOT NULL,
              PRIMARY KEY(tournament_id,profile_id));
            CREATE TABLE IF NOT EXISTS tournament_watchers(profile_id TEXT PRIMARY KEY REFERENCES profiles(id));
            CREATE TABLE IF NOT EXISTS tournament_intentions(
              tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
              profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
              created REAL NOT NULL, PRIMARY KEY(tournament_id,profile_id));
            CREATE TABLE IF NOT EXISTS tournament_rewards(
              tournament_id INTEGER NOT NULL REFERENCES tournaments(id), profile_id TEXT NOT NULL REFERENCES profiles(id),
              reward INTEGER NOT NULL, balances_json TEXT NOT NULL, awarded REAL NOT NULL,
              PRIMARY KEY(tournament_id,profile_id));
            CREATE TABLE IF NOT EXISTS profile_roles(profile_id TEXT PRIMARY KEY REFERENCES profiles(id), role TEXT NOT NULL CHECK(role IN ('player','moderator','admin')));
            CREATE TABLE IF NOT EXISTS sanctions(profile_id TEXT NOT NULL REFERENCES profiles(id),kind TEXT NOT NULL,expires REAL,reason TEXT NOT NULL,actor TEXT REFERENCES profiles(id),PRIMARY KEY(profile_id,kind));
            CREATE TABLE IF NOT EXISTS moderation_audit(id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT,target TEXT NOT NULL REFERENCES profiles(id),action TEXT NOT NULL,reason TEXT NOT NULL,expires REAL,created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS cosmetic_unlocks(profile_id TEXT NOT NULL REFERENCES profiles(id),item_id TEXT NOT NULL,created REAL NOT NULL,PRIMARY KEY(profile_id,item_id));
            CREATE TABLE IF NOT EXISTS economy_ledger(id INTEGER PRIMARY KEY AUTOINCREMENT,profile_id TEXT NOT NULL REFERENCES profiles(id),item_id TEXT NOT NULL,amount_json TEXT NOT NULL,created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS seasons(id INTEGER PRIMARY KEY,settings_json TEXT NOT NULL,closed REAL);
            CREATE TABLE IF NOT EXISTS season_rankings(season_id INTEGER NOT NULL REFERENCES seasons(id),profile_id TEXT NOT NULL REFERENCES profiles(id),statistics_json TEXT NOT NULL,PRIMARY KEY(season_id,profile_id));
            CREATE TABLE IF NOT EXISTS tournament_rounds(tournament_id INTEGER NOT NULL REFERENCES tournaments(id),round INTEGER NOT NULL,phase TEXT NOT NULL,eligible_json TEXT NOT NULL,PRIMARY KEY(tournament_id,round));
            CREATE TABLE IF NOT EXISTS admin_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS admin_events(id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT NOT NULL REFERENCES profiles(id),action TEXT NOT NULL,details TEXT NOT NULL,created REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS chat_by_match ON chat_messages(match_id,id);
            CREATE INDEX IF NOT EXISTS chat_by_pair ON chat_messages(sender,recipient,id);
            INSERT OR IGNORE INTO schema_versions VALUES(8);
        """)
        from backend.tracking import init_schema
        init_schema(self.db)
        from backend.matchmaking_metrics import init_schema as init_matchmaking_metrics
        init_matchmaking_metrics(self.db)

    @contextmanager
    def transaction(self):
        callbacks = []
        with self.lock:
            if self.closed: raise ServiceError("SERVICE_STOPPING", "Server is shutting down")
            self.db.execute("BEGIN IMMEDIATE")
            self.pending_notifications = set()
            self.commit_callbacks = []
            try:
                yield
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
            else:
                self.db.execute("COMMIT")
                for profile in self.pending_notifications:
                    self.notify(profile)
                callbacks = self.commit_callbacks
            finally:
                self.pending_notifications = set()
                self.commit_callbacks = []
        # Simulation must never keep the database locked while waiting on Bun.
        for callback in callbacks:
            callback()

    @contextmanager
    def watch(self, profile):
        """Register before checking the cursor, under the same lock as commit."""
        with self.lock:
            condition, count = self.waiters.get(profile, (threading.Condition(self.lock), 0))
            self.waiters[profile] = (condition, count + 1)
            try:
                yield condition
            finally:
                _, count = self.waiters[profile]
                if count == 1:
                    del self.waiters[profile]
                else:
                    self.waiters[profile] = (condition, count - 1)

    def notify(self, profile):
        if profile in self.waiters:
            self.waiters[profile][0].notify_all()

    def wake_all(self):
        with self.lock:
            for condition, _ in self.waiters.values():
                condition.notify_all()

    def after_commit(self, callback):
        self.commit_callbacks.append(callback)

    @staticmethod
    def digest(value):
        return hashlib.sha256(value.encode()).hexdigest()

    def create_profile(self, nickname, club):
        if not isinstance(nickname, str) or not 1 <= len(nickname.strip()) <= 30 or any(ord(c) < 32 for c in nickname):
            raise ServiceError("INVALID_NAME", "Choose a player name of 1–30 characters")
        identity = str(uuid.uuid4())
        nickname = nickname.strip()
        if self.db.execute("SELECT 1 FROM profiles WHERE nickname=?", (nickname,)).fetchone():
            nickname = nickname[:25] + " " + identity[:4]
        stats = fresh_statistics()
        self.db.execute("INSERT INTO profiles VALUES(?,?,?,?,?)",
                        (identity, nickname, json.dumps(club), json.dumps(stats), time.time()))
        return identity, self.issue_session(identity)

    def issue_session(self, identity, kind='device'):
        self.check_sanctions(identity)
        token = secrets.token_urlsafe(32)
        self.db.execute("INSERT INTO sessions(token_hash,profile_id,expires,kind) VALUES(?,?,?,?)",
                        (self.digest(token), identity, time.time() + 365 * 86400, kind))
        return token

    def session_kind(self, token):
        return self.db.execute('SELECT kind FROM sessions WHERE token_hash=?', (self.digest(token),)).fetchone()[0]

    def authenticate(self, token):
        with self.lock:
            if self.closed:
                raise ServiceError("SERVICE_STOPPING", "Server is shutting down")
            if not isinstance(token, str) or not 16 <= len(token) <= 128:
                raise ServiceError("SESSION_INVALID", "A valid device session is required")
            row = self.db.execute("SELECT profile_id FROM sessions WHERE token_hash=? AND expires>?",
                                  (self.digest(token), time.time())).fetchone()
            if not row:
                deleted = self.db.execute("SELECT 1 FROM deleted_sessions WHERE token_hash=? AND expires>?",
                                          (self.digest(token), time.time())).fetchone()
                if deleted:
                    raise ServiceError("SESSION_DELETED", "Ce profil a été supprimé. Aucune reconnexion automatique n’est possible.")
                raise ServiceError("SESSION_INVALID", "Device session expired or unknown")
            self.check_sanctions(row["profile_id"])
            return row["profile_id"]

    def check_sanctions(self, identity):
        row=self.db.execute("SELECT kind,reason FROM sanctions WHERE profile_id=? AND kind IN ('ban','kick') AND (expires IS NULL OR expires>?) ORDER BY kind LIMIT 1",(identity,time.time())).fetchone()
        if row:raise ServiceError('PLAYER_BANNED' if row['kind']=='ban' else 'PLAYER_KICKED',row['reason'])

    def profile(self, identity):
        row = self.db.execute("SELECT * FROM profiles WHERE id=?", (identity,)).fetchone()
        if not row:
            raise ServiceError("PROFILE_UNKNOWN", "Unknown profile")
        return {"id": identity, "nickname": row["nickname"], "club": json.loads(row["club_json"]),
                "statistics": json.loads(row["statistics_json"])}

    def save_club(self, identity, club):
        self.db.execute("UPDATE profiles SET club_json=? WHERE id=?", (json.dumps(club), identity))

    def save_match(self, match):
        self.db.execute("UPDATE matches SET state_json=?,updated=? WHERE id=?",
                        (json.dumps(match), time.time(), match["id"]))

    def match(self, identity):
        row = self.db.execute("SELECT state_json FROM matches WHERE id=?", (identity,)).fetchone()
        if not row:
            raise ServiceError("MATCH_UNKNOWN", "Unknown match")
        return json.loads(row["state_json"])

    def active_match(self, profile):
        rows = self.db.execute("SELECT m.state_json FROM matches m JOIN participants p ON p.match_id=m.id "
                               "WHERE p.profile_id=? ORDER BY m.id DESC", (profile,)).fetchall()
        for row in rows:
            match = json.loads(row["state_json"])
            if match["phase"] != "ended":
                return match
        return None

    def emit(self, profile, packet):
        self.emit_many((profile,), packet)

    def emit_many(self, profiles, packet):
        profiles = tuple(dict.fromkeys(p for p in profiles if p is not None))
        if not profiles:
            return
        now = time.time()
        payload = json.dumps({"created_at": now, **packet})
        self.db.executemany("INSERT INTO events(profile_id,packet_json,created) VALUES(?,?,?)",
                            ((profile, payload, now) for profile in profiles))
        if self.db.in_transaction:
            self.pending_notifications.update(profiles)
        else:
            with self.lock:
                for profile in profiles:
                    self.notify(profile)

    def poll(self, profile, cursor):
        if not isinstance(cursor, int) or isinstance(cursor, bool) or cursor < 0:
            raise ServiceError("INVALID_CURSOR", "Event cursor must be a nonnegative integer")
        rows = self.db.execute("SELECT seq,packet_json FROM events WHERE profile_id=? AND seq>? ORDER BY seq LIMIT 32",
                               (profile, cursor)).fetchall()
        return [{"seq": row["seq"], **json.loads(row["packet_json"])} for row in rows]

    def reward(self, match, side):
        profile = match["profiles"][side - 1]
        if profile is None:
            return
        score = match["score"]
        outcome = "draws" if score[0] == score[1] else "wins" if score[side - 1] > score[2 - side] else "defeats"
        inserted = self.db.execute("INSERT OR IGNORE INTO match_results VALUES(?,?,?)", (match["id"], profile, outcome)).rowcount
        if inserted:
            statistics = self.profile(profile)["statistics"]
            kind=result_kind(match)
            if kind=='ranked':
                lifetime=statistics.setdefault('lifetime_ranked',{'wins':0,'draws':0,'defeats':0})
                lifetime[outcome]+=1
            if kind=='ranked' and match.get('season_id') is not None and statistics.get('season_id')!=match['season_id']:
                row=self.db.execute('SELECT statistics_json FROM season_rankings WHERE season_id=? AND profile_id=?',(match['season_id'],profile)).fetchone()
                historical=json.loads(row[0]) if row else {'wins':0,'draws':0,'defeats':0,'rating':1000}
                credit(historical,kind,outcome)
                self.db.execute('INSERT OR REPLACE INTO season_rankings VALUES(?,?,?)',(match['season_id'],profile,json.dumps(historical)))
            else:credit(statistics,kind,outcome)
            self.db.execute("UPDATE profiles SET statistics_json=? WHERE id=?", (json.dumps(statistics), profile))

    def backup(self, destination):
        with self.lock, sqlite3.connect(str(destination)) as target:
            self.db.backup(target)

    def close(self):
        with self.changed:
            if not self.closed:
                self.closed = True
                self.db.close()
            self.changed.notify_all()
            self.wake_all()
