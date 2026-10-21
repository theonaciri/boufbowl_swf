"""Local role assignment resolves accounts explicitly and never resets databases."""
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from backend.storage import Store


class ManageRoleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.database = Path(self.temporary.name) / 'state.sqlite'
        store = Store(self.database)
        self.profile, _ = store.create_profile('Local Player', [])
        store.db.execute('INSERT INTO accounts(username,profile_id,salt,password_hash,iterations,created) VALUES(?,?,?,?,?,?)',
                         ('operator', self.profile, 'test', 'not-a-login-hash', 1, 0))
        store.close()

    def tearDown(self):
        self.temporary.cleanup()

    def command(self, *arguments, database=None):
        return subprocess.run([sys.executable, '-m', 'backend.manage', '--database', str(database or self.database),
                               'role', *arguments], capture_output=True, text=True, timeout=10)

    def test_account_username_can_differ_from_nickname_and_matches_without_case(self):
        result = self.command('--account', 'OpErAtOr', 'admin')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('operator (game nickname: Local Player): admin', result.stdout)
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute('SELECT profile_id,role FROM profile_roles').fetchall(), [(self.profile, 'admin')])
            self.assertEqual(db.execute('SELECT target,action FROM moderation_audit').fetchall(), [(self.profile, 'role')])

    def test_explicit_lookup_distinguishes_a_nickname_matching_another_account(self):
        store = Store(self.database)
        other, _ = store.create_profile('operator', [])
        store.close()
        self.assertEqual(self.command('operator', 'moderator').returncode, 0)
        self.assertEqual(self.command('--account', 'operator', 'admin').returncode, 0)
        with sqlite3.connect(self.database) as db:
            roles = dict(db.execute('SELECT profile_id,role FROM profile_roles'))
            self.assertEqual(roles, {other: 'moderator', self.profile: 'admin'})

    def test_username_used_without_account_flag_explains_the_mismatch(self):
        result = self.command('operator', 'admin')
        self.assertEqual(result.returncode, 2)
        self.assertIn('--account', result.stderr)
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM profile_roles').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM moderation_audit').fetchone()[0], 0)

    def test_missing_database_is_not_created(self):
        missing = Path(self.temporary.name) / 'missing.sqlite'
        result = self.command('--account', 'operator', 'admin', database=missing)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(missing.exists())

    def test_incompatible_database_is_not_reset(self):
        old = Path(self.temporary.name) / 'old.sqlite'
        with sqlite3.connect(old) as db:
            db.executescript("CREATE TABLE schema_versions(version INTEGER); INSERT INTO schema_versions VALUES(7); CREATE TABLE preserved(value TEXT); INSERT INTO preserved VALUES('keep');")
        result = self.command('--account', 'operator', 'admin', database=old)
        self.assertEqual(result.returncode, 2)
        self.assertIn('left unchanged', result.stderr)
        with sqlite3.connect(old) as db:
            self.assertEqual(db.execute('SELECT value FROM preserved').fetchone()[0], 'keep')
            self.assertEqual(db.execute('SELECT version FROM schema_versions').fetchone()[0], 7)
