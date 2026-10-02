"""Separate durable stores coordinated by one local SQLite transaction.

All attached stores use DELETE journals + FULL synchronous. Unlike WAL, SQLite's
super-journal provides atomic commit across attached on-disk databases. Use only
a local filesystem, one process, and this connection boundary for every write.
"""
import hashlib
import json
import sqlite3
import threading
from contextlib import closing
from pathlib import Path

VERSION = 1
STORES = {
    'auth': ('accounts', 'sessions', 'login_attempts', 'token_usage', 'usage_migrations'),
    'users': ('profiles',),
    'conversations': ('conversations', 'chats', 'feedback', 'quality_reports', 'quality_migrations'),
    'knowledge': ('docs', 'source_sync'),
    'audit': ('audit',),
    'archive': (),
}
AUTH_COLUMNS = ('id', 'username', 'role', 'password_hash', 'active', 'created', 'updated',
                'model', 'monthly_token_limit', 'allowed_models')
PROFILE_COLUMNS = ('id', 'name', 'customers')
USER_COLUMNS = ('id', 'username', 'name', 'role', 'customers', 'password_hash', 'active',
                'created', 'updated', 'model', 'monthly_token_limit', 'allowed_models')
GATE = threading.RLock()


def paths(root):
    root = Path(root).resolve()
    return {name: root / name / (name + '.sqlite3') for name in STORES}


def validate(root, integrity=False):
    root = Path(root).resolve()
    try:
        manifest = json.loads((root / 'layout.json').read_text(encoding='utf8'))
        if manifest['version'] != VERSION or set(manifest['stores']) != set(STORES):
            raise ValueError('Unsupported database layout')
        for name, path in paths(root).items():
            if not path.is_file():
                raise ValueError('Missing store: ' + name)
            with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as c:
                if c.execute('PRAGMA user_version').fetchone()[0] != VERSION:
                    raise ValueError('Unsupported schema: ' + name)
                if c.execute('PRAGMA journal_mode').fetchone()[0] != 'delete':
                    raise ValueError('Stores must use DELETE journals, not WAL: ' + name)
                tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not set(STORES[name]) <= tables:
                    raise ValueError('Missing tables: ' + name)
                if integrity and c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('Database integrity failure: ' + name)
    except (OSError, KeyError, TypeError, sqlite3.Error) as exc:
        raise ValueError('Data not initialized. Run operations init/migrate into a NEW directory; check APP_DATA_DIR.') from exc
    return manifest


class Connection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()

    def close(self):
        try:
            super().close()
        finally:
            if getattr(self, '_owns_gate', False):
                self._owns_gate = False
                GATE.release()


def connect(root):
    """SQL compatibility facade; no runtime CREATE/ALTER on persistent schemas."""
    files = paths(root)
    if not (Path(root) / 'layout.json').is_file() or any(not p.is_file() for p in files.values()):
        raise RuntimeError('Missing initialized stores. Refusing to create empty databases.')
    GATE.acquire()
    c = None
    try:
        c = sqlite3.connect(files['auth'].as_uri() + '?mode=rw', uri=True,
                            timeout=30, factory=Connection)
        c._owns_gate = True
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA busy_timeout=30000')
        c.execute('PRAGMA foreign_keys=ON')
        c.execute('PRAGMA synchronous=FULL')
        for name, path in files.items():
            if name == 'auth':
                continue
            c.execute(f'ATTACH DATABASE ? AS {name}', (path.as_uri() + '?mode=rw',))
            c.execute(f'PRAGMA {name}.synchronous=FULL')
        # The old API's users record is now a join, never a persisted combined table.
        projection = ','.join('p.' + col if col in ('name', 'customers') else 'a.' + col
                              for col in USER_COLUMNS)
        c.execute(f'CREATE TEMP VIEW users AS SELECT {projection} FROM main.accounts a '
                  'JOIN users.profiles p ON p.id=a.id')
        for operation in ('INSERT', 'UPDATE', 'DELETE'):
            if operation == 'INSERT':
                statements = 'INSERT INTO accounts VALUES(' + ','.join('NEW.' + x for x in AUTH_COLUMNS) + ');'
                statements += 'INSERT INTO profiles VALUES(' + ','.join('NEW.' + x for x in PROFILE_COLUMNS) + ');'
            elif operation == 'UPDATE':
                statements = 'UPDATE accounts SET ' + ','.join(x + '=NEW.' + x for x in AUTH_COLUMNS) + ' WHERE id=OLD.id;'
                statements += 'UPDATE profiles SET ' + ','.join(x + '=NEW.' + x for x in PROFILE_COLUMNS) + ' WHERE id=OLD.id;'
            else:
                statements = 'DELETE FROM profiles WHERE id=OLD.id;DELETE FROM accounts WHERE id=OLD.id;'
            c.execute(f'CREATE TEMP TRIGGER users_{operation.lower()} INSTEAD OF {operation} ON users '
                      f'BEGIN {statements} END')
        return c
    except BaseException:
        if c is not None:
            c.close()
        else:
            GATE.release()
        raise


def digest_table(c, table):
    """Order-independent comparison; hashes only, never secret values in reports."""
    quoted = '"' + table.replace('"', '""') + '"'
    columns=sorted(r[1] for r in c.execute('PRAGMA table_info('+quoted+')'))
    projection=','.join('"'+col.replace('"','""')+'"' for col in columns)
    rows = sorted(hashlib.sha256(json.dumps(tuple(row), ensure_ascii=False,
                  separators=(',', ':')).encode()).hexdigest() for row in c.execute('SELECT '+projection+' FROM ' + quoted))
    return {'count': len(rows), 'sha256': hashlib.sha256(''.join(rows).encode()).hexdigest()}