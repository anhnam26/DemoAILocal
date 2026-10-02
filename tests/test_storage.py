"""Offline storage/migration/backup tests. No credentials or provider requests."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from cyberant import accounts, config, operations, storage, sync_knowledge, token_usage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cyberant-storage-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / 'runtime'
        self.values = {'APP_DATA_DIR': str(self.data), 'APP_ENV': 'development',
                       'BOOTSTRAP_ADMIN_PASSWORD': 'Offline-fixture-password',
                       'MODEL': 'test/offline', 'DEFAULT_MONTHLY_TOKENS': '1000'}
        self.patcher = patch('cyberant.config.env', return_value=self.values)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        operations.initialize(self.data)
        self.connect = lambda: storage.connect(self.data)
        with self.connect() as c:
            self.id = c.execute('SELECT id FROM users').fetchone()[0]

    def test_separate_accounts_profiles_and_atomic_rollback(self):
        with closing(sqlite3.connect(storage.paths(self.data)['auth'])) as c:
            cols = {r[1] for r in c.execute('PRAGMA table_info(accounts)')}
            self.assertNotIn('name', cols)
            self.assertNotIn('customers', cols)
        with closing(sqlite3.connect(storage.paths(self.data)['users'])) as c:
            cols = {r[1] for r in c.execute('PRAGMA table_info(profiles)')}
            self.assertNotIn('password_hash', cols)
        with self.connect() as c:
            before = dict(c.execute('SELECT * FROM users').fetchone())
        with self.assertRaises(RuntimeError):
            with self.connect() as c:
                c.execute("UPDATE users SET username='changed',name='Changed' WHERE id=?", (self.id,))
                c.execute("INSERT INTO audit(ts,action,role,detail) VALUES('now','test','admin','rollback')")
                raise RuntimeError('Injected failure')
        with self.connect() as c:
            self.assertEqual(before, dict(c.execute('SELECT * FROM users').fetchone()))
            self.assertEqual(c.execute('SELECT COUNT(*) FROM audit').fetchone()[0], 0)

    def test_backup_restore_checksums_and_no_overwrite(self):
        backup = self.root / 'backup'
        operations.backup(self.data, backup)
        restored = self.root / 'restored'
        operations.restore(backup, restored)
        with self.connect() as a, storage.connect(restored) as b:
            for table in ('users', 'docs', 'token_usage', 'conversations', 'audit'):
                self.assertEqual(storage.digest_table(a, table), storage.digest_table(b, table))
        with self.assertRaises(ValueError):
            operations.restore(backup, restored)
        with self.assertRaises(ValueError):
            operations.initialize(self.data)
        path = storage.paths(backup)['knowledge']
        with path.open('ab') as file:
            file.write(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            operations.restore(backup, self.root / 'bad-restore')
        self.assertFalse((self.root / 'bad-restore').exists())

    def test_legacy_migration_is_lossless_and_keeps_unknown_tables(self):
        legacy = self.root / 'legacy.sqlite3'
        with self.connect() as src, closing(sqlite3.connect(legacy)) as dest:
            for name in storage.STORES:
                with closing(sqlite3.connect(':memory:')) as part:
                    src.backup(part, name='main' if name == 'auth' else name)
                    for line in part.iterdump():
                        if line not in ('BEGIN TRANSACTION;', 'COMMIT;'):
                            dest.execute(line)
            dest.execute('CREATE TABLE users AS SELECT a.*,p.name,p.customers FROM accounts a JOIN profiles p ON p.id=a.id')
            dest.execute('DROP TABLE accounts')
            dest.execute('DROP TABLE profiles')
            dest.execute('CREATE TABLE old_business(id INTEGER PRIMARY KEY,payload TEXT)')
            dest.execute("INSERT INTO old_business VALUES(7,'preserved')")
            dest.execute('INSERT INTO sessions(token,profile,created,user_id) VALUES(?,?,?,?)', ('old-token', 'admin', 1, self.id))
            dest.commit()
        before = hashlib.sha256(legacy.read_bytes()).hexdigest()
        target = self.root / 'migrated'
        report = operations.migrate(legacy, target)
        self.assertEqual(before, hashlib.sha256(legacy.read_bytes()).hexdigest())
        self.assertIn('old_business', report['archived_tables'])
        self.assertEqual(report['sessions_revoked'], 1)
        with storage.connect(target) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM sessions').fetchone()[0], 0)
            self.assertEqual(c.execute('SELECT payload FROM old_business').fetchone()[0], 'preserved')
            self.assertTrue(accounts.verify(self.values['BOOTSTRAP_ADMIN_PASSWORD'], c.execute('SELECT password_hash FROM users').fetchone()[0]))

    def test_quota_concurrency_restart_uncertain_and_chat_independence(self):
        def reserve(_):
            try:
                return token_usage.reserve(self.connect, self.id, 'test/offline', 100, 100)[0]
            except Exception as exc:
                from fastapi import HTTPException
                if isinstance(exc, HTTPException) and exc.status_code == 429:
                    return None
                raise
        with ThreadPoolExecutor(max_workers=8) as pool:
            reservations = [id for id in pool.map(reserve, range(12)) if id]
        self.assertEqual(len(reservations), 5)
        token_usage.mark_sent(self.connect, reservations[0])
        token_usage.recover(self.connect)
        result = token_usage.summary(self.connect, self.id)
        self.assertEqual(result['uncertain_tokens'], 200)
        self.assertEqual(result['reserved_tokens'], 0)
        token_usage.reconcile(self.connect, reservations[0], 75, 25, 'Offline test reconciliation')
        with self.connect() as c:
            c.execute('DELETE FROM chats')
        self.assertEqual(token_usage.summary(self.connect, self.id)['used_tokens'], 100)

    def test_manifest_failure_does_not_modify_runtime(self):
        with self.connect() as c:
            before = storage.digest_table(c, 'docs')
        corpus = self.root / 'corpus'
        corpus.mkdir()
        (corpus / 'manifest.json').write_text(json.dumps({'version': 1, 'documents': [
            {'id': 'MISSING', 'path': 'documents/A/MISSING.json', 'sha256': 'bad'}]}))
        with self.assertRaises(OSError):
            sync_knowledge.load(corpus / 'manifest.json')
        with self.connect() as c:
            self.assertEqual(before, storage.digest_table(c, 'docs'))

    def test_import_does_not_create_runtime_or_accept_missing_store(self):
        target = self.root / 'must-not-exist'
        code = "import os;os.environ['APP_DATA_DIR']=" + repr(str(target)) + ";import cyberant.app"
        subprocess.run([sys.executable, '-B', '-c', code], check=True, cwd=config.ROOT)
        self.assertFalse(target.exists())
        storage.paths(self.data)['archive'].unlink()
        with self.assertRaises((RuntimeError, ValueError)):
            self.connect()
        self.assertFalse(storage.paths(self.data)['archive'].exists())


if __name__ == '__main__':
    unittest.main()