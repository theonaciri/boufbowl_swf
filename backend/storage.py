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


class ServiceError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


class Store:
    def __init__(self, path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA foreign_keys=ON;
            PRAGMA journal_mode=WAL;
            PRAGMA busy_timeout=10000;
            CREATE TABLE IF NOT EXISTS schema_versions(version INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS profiles(
              id TEXT PRIMARY KEY, nickname TEXT NOT NULL COLLATE NOCASE UNIQUE,
              club_json TEXT NOT NULL, statistics_json TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(
              token_hash TEXT PRIMARY KEY, profile_id TEXT NOT NULL REFERENCES profiles(id), expires REAL NOT NULL);
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
              message TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS spectators(
              profile_id TEXT PRIMARY KEY REFERENCES profiles(id),
              match_id INTEGER NOT NULL REFERENCES matches(id));
            INSERT OR IGNORE INTO schema_versions VALUES(1);
        """)
        version = self.db.execute("SELECT MAX(version) FROM schema_versions").fetchone()[0]
        if version != 1:
            raise ServiceError("DATABASE_VERSION", "Unsupported database version")

    @contextmanager
    def transaction(self):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
            else:
                self.db.execute("COMMIT")

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
        stats = {"wins": 0, "draws": 0, "defeats": 0, "rating": 1000}
        self.db.execute("INSERT INTO profiles VALUES(?,?,?,?,?)",
                        (identity, nickname, json.dumps(club), json.dumps(stats), time.time()))
        token = secrets.token_urlsafe(32)
        self.db.execute("INSERT INTO sessions VALUES(?,?,?)",
                        (self.digest(token), identity, time.time() + 365 * 86400))
        return identity, token

    def authenticate(self, token):
        if not isinstance(token, str) or not 16 <= len(token) <= 128:
            raise ServiceError("SESSION_INVALID", "A valid device session is required")
        row = self.db.execute("SELECT profile_id FROM sessions WHERE token_hash=? AND expires>?",
                              (self.digest(token), time.time())).fetchone()
        if not row:
            raise ServiceError("SESSION_INVALID", "Device session expired or unknown")
        return row["profile_id"]

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
        if profile is not None:
            self.db.execute("INSERT INTO events(profile_id,packet_json,created) VALUES(?,?,?)",
                            (profile, json.dumps(packet), time.time()))

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
            statistics[outcome] += 1
            statistics["rating"] = max(0, statistics["rating"] + (20 if outcome == "wins" else -20 if outcome == "defeats" else 0))
            self.db.execute("UPDATE profiles SET statistics_json=? WHERE id=?", (json.dumps(statistics), profile))

    def backup(self, destination):
        with self.lock, sqlite3.connect(str(destination)) as target:
            self.db.backup(target)

    def close(self):
        with self.lock:
            self.db.close()
