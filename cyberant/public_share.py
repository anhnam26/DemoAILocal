"""Opt-in temporary Linux sharing; no .env writes, installs or AI calls."""
import os
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from cyberant import config,storage

URL_PATTERN = re.compile(r'https://[a-z0-9]+(?:-[a-z0-9]+)*\.trycloudflare\.com(?=$|[\s|\"\x1b])')


def private_path(path, directory=False):
    info = path.stat()
    if info.st_uid != os.geteuid() or info.st_mode & 0o077:
        mode = '700' if directory else '600'
        raise ValueError(f'{path} must be owned by the service user with chmod {mode}; permissions were not changed.')


def preflight(root, data_dir, executable):
    if sys.platform != 'linux':
        raise ValueError('--share is supported on Linux only.')
    if os.geteuid() == 0:
        raise ValueError('Do not share as root. Use a dedicated unprivileged Linux account.')
    binary = shutil.which(executable)
    if not binary:
        raise ValueError('cloudflared not found. Install it from the official Cloudflare package repository first.')
    env_file = config.env_path()
    if env_file.exists():
        private_path(env_file)
    storage.validate(data_dir)
    private_path(data_dir, directory=True)
    private_path(data_dir/'layout.json')
    for path in storage.paths(data_dir).values():
        private_path(path.parent,directory=True)
        private_path(path)
        for suffix in ('-journal','-wal','-shm'):
            sidecar=Path(str(path)+suffix)
            if sidecar.exists():private_path(sidecar)
    if (data_dir / 'initial-accounts.json').exists():
        raise ValueError('Remove plaintext initial-accounts.json from the server before sharing; rotate any exposed passwords.')
    directories = [Path.home() / name for name in ('.cloudflared', '.cloudflare-warp', 'cloudflare-warp')]
    directories += [Path('/etc/cloudflared'), Path('/usr/local/etc/cloudflared')]
    for directory in directories:
        if any((directory / name).exists() for name in ('config.yml', 'config.yaml')):
            raise ValueError(f'Existing cloudflared configuration in {directory}. Use a dedicated account/host without named-tunnel config.')
    return str(Path(binary).resolve())


def validate_database(data_dir):
    """Called under the instance lock, before any public connection."""
    storage.validate(data_dir,integrity=True)
    uri = storage.paths(data_dir)['auth'].as_uri() + '?mode=ro'
    connection = None
    try:
        connection = sqlite3.connect(uri, uri=True)
        active = connection.execute("SELECT COUNT(*) FROM accounts WHERE role='admin' AND active=1").fetchone()[0]
    except sqlite3.Error:
        raise ValueError('Existing database is not initialized correctly. Check it privately before sharing.') from None
    finally:
        if connection is not None:
            connection.close()
    if not active:
        raise ValueError('An active administrator account is required before sharing.')


class QuickTunnel:
    def __init__(self, executable, port, protocol='auto'):
        self.executable = executable
        self.port = port
        self.protocol = protocol
        self.process = None
        self.reader = None
        self.url = None
        self.connected = threading.Event()
        self.cancelled = threading.Event()
        self.handlers = {}
        self.close_lock = threading.Lock()

    def __enter__(self):
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            self.handlers[signum] = signal.signal(signum, self._cancel)
        return self

    def _cancel(self, signum, frame):
        self.cancelled.set()

    def _read(self):
        # Drain logs without retaining or printing raw tunnel credentials.
        for line in self.process.stdout:
            match = URL_PATTERN.search(line)
            if match and self.url is None:
                self.url = match.group(0)
            if 'Registered tunnel connection' in line:
                self.connected.set()

    def start(self, timeout=90):
        # Do not pass app/API secrets or TUNNEL_* overrides to cloudflared.
        allowed = ('PATH', 'HOME', 'LANG', 'LC_ALL', 'TMPDIR', 'SSL_CERT_FILE', 'SSL_CERT_DIR')
        environment = {key: os.environ[key] for key in allowed if key in os.environ}
        self.process = subprocess.Popen(
            [self.executable, 'tunnel', '--no-autoupdate', '--config', '',
             '--url', f'http://127.0.0.1:{self.port}', '--protocol', self.protocol,
             '--metrics', '127.0.0.1:0', '--loglevel', 'info'],
            env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
            start_new_session=True,
        )
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.cancelled.is_set():
                raise KeyboardInterrupt
            if self.process.poll() is not None:
                raise RuntimeError('cloudflared exited before connecting. Check its version, outbound network and existing config.')
            if self.url and self.connected.is_set():
                return self.url
            time.sleep(0.1)
        raise RuntimeError('Tunnel startup timed out. Check outbound connectivity; try --share-protocol http2 if UDP is blocked.')

    def close(self):
        with self.close_lock:
            if self.process is not None:
                if self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait()
                if self.reader is not None:
                    self.reader.join(timeout=2)
                if self.process.stdout is not None:
                    self.process.stdout.close()

    def __exit__(self, *exc):
        try:
            self.close()
        finally:
            for signum, handler in self.handlers.items():
                signal.signal(signum, handler)


def serve(server, listener, executable, port, protocol):
    """Reserve the listener and DB lock before reaching this function."""
    from cyberant import config
    overrides = {'APP_ENV': 'production', 'APP_HOST': '127.0.0.1', 'APP_PORT': str(port)}
    previous = {key: os.environ.get(key) for key in (*overrides, 'APP_ORIGINS')}
    finished = threading.Event()
    failed = threading.Event()
    monitor = None
    print('Temporary PUBLIC sharing: login required; Cloudflare carries web traffic.', flush=True)
    print('No SLA/SSE. Long AI requests may time out; do not automatically resubmit them.', flush=True)
    try:
        with QuickTunnel(executable, port, protocol) as tunnel:
            url = tunnel.start()
            os.environ.update(overrides, APP_ORIGINS=url)
            config.security()
            if tunnel.cancelled.is_set():
                raise KeyboardInterrupt

            def watch():
                announced = False
                deadline = time.monotonic() + 120
                while not finished.wait(0.1):
                    if tunnel.process.poll() is not None:
                        failed.set()
                        print('Tunnel stopped unexpectedly; stopping the app. No automatic restart.', flush=True)
                        server.should_exit = True
                        return
                    if tunnel.cancelled.is_set() or server.should_exit:
                        server.should_exit = True
                        tunnel.close()
                        return
                    if not server.started and time.monotonic() > deadline:
                        failed.set()
                        print('Application startup timed out; closing public access.', flush=True)
                        server.should_exit = True
                        tunnel.close()
                        return
                    if server.started and not announced:
                        print(f'Public URL: {url}\nPress Ctrl+C to close sharing. New sessions require login.', flush=True)
                        print('Local app and tunnel connected; public reachability still depends on Cloudflare/network.', flush=True)
                        announced = True

            monitor = threading.Thread(target=watch, daemon=True)
            monitor.start()
            try:
                server.run(sockets=[listener])
            finally:
                finished.set()
                monitor.join(timeout=15)
            if failed.is_set():
                raise RuntimeError('Sharing session failed; see the startup/shutdown message above.')
    finally:
        finished.set()
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

