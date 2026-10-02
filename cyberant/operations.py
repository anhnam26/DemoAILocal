"""Explicit init/migrate/check/backup/restore; never alter a legacy source DB."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
from contextlib import closing

from cyberant import config, legacy, runtime_lock, storage, sync_knowledge


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def _legacy_connect(path):
    c = sqlite3.connect(path, factory=storage.Connection)
    c.row_factory = sqlite3.Row
    return c


def _new_destination(target):
    target = Path(target).resolve()
    if target.exists():
        raise ValueError('Destination must NOT exist; source/runtime data will never be overwritten: ' + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _export(snapshot, destination):
    files = storage.paths(destination)
    for path in files.values():
        path.parent.mkdir(parents=True, mode=0o700)
    source = _legacy_connect(snapshot)
    connections = {name: sqlite3.connect(path) for name, path in files.items()}
    try:
        for c in connections.values():
            c.execute('PRAGMA journal_mode=DELETE')
            c.execute('PRAGMA synchronous=FULL')
            c.execute(f'PRAGMA user_version={storage.VERSION}')
        connections['auth'].execute('''CREATE TABLE accounts(
            id TEXT PRIMARY KEY,username TEXT UNIQUE COLLATE NOCASE NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','member')),password_hash TEXT NOT NULL,
            active INTEGER NOT NULL CHECK(active IN (0,1)),created REAL NOT NULL,updated REAL NOT NULL,
            model TEXT NOT NULL DEFAULT '',monthly_token_limit INTEGER NOT NULL CHECK(monthly_token_limit>=0),
            allowed_models TEXT NOT NULL)''')
        connections['users'].execute('CREATE TABLE profiles(id TEXT PRIMARY KEY,name TEXT NOT NULL,customers TEXT NOT NULL)')
        for row in source.execute('SELECT * FROM users'):
            for name, table, columns in (('auth', 'accounts', storage.AUTH_COLUMNS),
                                         ('users', 'profiles', storage.PROFILE_COLUMNS)):
                connections[name].execute('INSERT INTO ' + table + ' VALUES(' + ','.join('?' for _ in columns) + ')',
                                          tuple(row[col] for col in columns))
        known = {table: name for name, tables in storage.STORES.items() for table in tables}
        report = {'tables': {}, 'archived_tables': [], 'sessions_revoked': 0}
        for table, sql in source.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
            if table == 'users':
                continue
            name = known.get(table, 'archive')
            if name == 'archive':
                report['archived_tables'].append(table)
            c = connections[name]
            c.execute(sql)
            quoted = '"' + table.replace('"', '""') + '"'
            rows = source.execute('SELECT * FROM ' + quoted).fetchall()
            if rows:
                c.executemany('INSERT INTO ' + quoted + ' VALUES(' + ','.join('?' for _ in rows[0]) + ')', rows)
            # Recreate indexes in their owning store.
            for (index_sql,) in source.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL", (table,)):
                c.execute(index_sql)
            before, after = storage.digest_table(source, table), storage.digest_table(c, table)
            if before != after:
                raise ValueError('Migration comparison failed: ' + table)
            report['tables'][table] = before
        for c in connections.values():
            c.commit()
        _write_json(destination / 'layout.json', {'version': storage.VERSION, 'stores': list(storage.STORES)})
        with storage.connect(destination) as c:
            before, after = storage.digest_table(source, 'users'), storage.digest_table(c, 'users')
            if before != after:
                raise ValueError('Account/profile comparison failed')
            report['tables']['users'] = before
            report['sessions_revoked'] = c.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
            c.execute('DELETE FROM sessions')
        storage.validate(destination, integrity=True)
        _write_json(destination / 'migration-report.json', report)
        return report
    finally:
        source.close()
        for c in connections.values():
            c.close()


def initialize(target):
    target = _new_destination(target)
    with tempfile.TemporaryDirectory(prefix='.cyberant-init-', dir=target.parent) as temp:
        temp = Path(temp)
        snapshot = temp / 'seed.sqlite3'
        connect = lambda: _legacy_connect(snapshot)
        legacy.upgrade(connect)
        sync_knowledge.synchronize(connect, sync_knowledge.load())
        result = temp / 'result'
        result.mkdir(mode=0o700)
        report = _export(snapshot, result)
        result.rename(target)
    return report


def migrate(source, target):
    source = Path(source).resolve()
    if not source.is_file():
        raise ValueError('Legacy source does not exist')
    target = _new_destination(target)
    # Refuse concurrent application writes; consistent backup then upgrade only the copy.
    lock = runtime_lock.acquire(source.parent)
    try:
        with tempfile.TemporaryDirectory(prefix='.cyberant-migrate-', dir=target.parent) as temp:
            temp = Path(temp)
            snapshot = temp / 'legacy.sqlite3'
            with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as src, closing(sqlite3.connect(snapshot)) as dest:
                src.backup(dest)
                if dest.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('Legacy database integrity failure')
                # No bootstrap account may be invented when migrating an invalid legacy DB.
                if not dest.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
                    raise ValueError('Legacy database has no accounts; use init for a new installation')
            legacy.upgrade(lambda: _legacy_connect(snapshot))
            result = temp / 'result'
            result.mkdir(mode=0o700)
            report = _export(snapshot, result)
            result.rename(target)
        return report
    finally:
        lock.close()


def backup(root, target):
    target = _new_destination(target)
    storage.validate(root)
    with tempfile.TemporaryDirectory(prefix='.cyberant-backup-', dir=target.parent) as temp:
        result = Path(temp) / 'result'
        result.mkdir(mode=0o700)
        manifest = {'version': storage.VERSION, 'created': datetime.now(timezone.utc).isoformat(), 'files': {}}
        # Every application DB connection owns GATE, including login/admin writes.
        # The gate is held across all snapshots: no mixed-time backup is possible.
        with storage.connect(root) as src:
            for name, path in storage.paths(result).items():
                path.parent.mkdir(mode=0o700)
                with closing(sqlite3.connect(path)) as dest:
                    src.backup(dest, name='main' if name == 'auth' else name)
                relative = path.relative_to(result).as_posix()
                manifest['files'][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        shutil.copyfile(Path(root) / 'layout.json', result / 'layout.json')
        manifest['files']['layout.json'] = hashlib.sha256((result / 'layout.json').read_bytes()).hexdigest()
        _write_json(result / 'backup.json', manifest)
        storage.validate(result, integrity=True)
        result.rename(target)
    return manifest


def restore(source, target):
    source = Path(source).resolve()
    target = _new_destination(target)
    manifest = json.loads((source / 'backup.json').read_text(encoding='utf8'))
    expected = {p.relative_to(source).as_posix() for p in storage.paths(source).values()} | {'layout.json'}
    if manifest.get('version') != storage.VERSION or set(manifest.get('files', {})) != expected:
        raise ValueError('Invalid backup manifest')
    for relative, digest in manifest['files'].items():
        if hashlib.sha256((source / relative).read_bytes()).hexdigest() != digest:
            raise ValueError('Backup checksum mismatch: ' + relative)
    storage.validate(source, integrity=True)
    with tempfile.TemporaryDirectory(prefix='.cyberant-restore-', dir=target.parent) as temp:
        result = Path(temp) / 'result'
        result.mkdir(mode=0o700)
        for relative in expected:
            destination = result / relative
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            shutil.copyfile(source / relative, destination)
        with storage.connect(result) as c:
            c.execute('DELETE FROM sessions')
        storage.validate(result, integrity=True)
        result.rename(target)


def main(argv=None):
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('init', 'migrate', 'backup', 'restore'):
        command = commands.add_parser(name)
        command.add_argument('--target', required=True, help='NEW, nonexistent destination directory')
        if name in ('migrate', 'restore'):
            command.add_argument('--source', required=True)
    commands.add_parser('check')
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            result = initialize(args.target)
        elif args.command == 'migrate':
            result = migrate(args.source, args.target)
        elif args.command == 'restore':
            restore(args.source, args.target)
            result = {'status': 'restored', 'sessions': 'revoked'}
        else:
            lock = runtime_lock.acquire(config.data_dir())
            try:
                result = (backup(config.data_dir(), args.target) if args.command == 'backup'
                          else storage.validate(config.data_dir(), integrity=True))
            finally:
                lock.close()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        parser.exit(1, f'Operation failed; original data was not overwritten: {exc}\n')


if __name__ == '__main__':
    main()