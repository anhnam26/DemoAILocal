"""Exercise Windows launchers with isolated data and no provider traffic."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from cyberant import config, operations


@unittest.skipUnless(os.name == 'nt', 'Windows launchers')
class LauncherTests(unittest.TestCase):
    def test_ready_duplicate_stop_and_missing_data(self):
        with tempfile.TemporaryDirectory(prefix='cyberant-launch-') as temp:
            root = Path(temp)
            data = root / 'runtime'
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0))
                port = listener.getsockname()[1]
            values = dict(APP_DATA_DIR=str(data), APP_ENV='development', MODEL='test/offline',
                          BOOTSTRAP_ADMIN_PASSWORD='Offline-launcher-password')
            with patch('cyberant.config.env', return_value=values):
                operations.initialize(data)
            envfile = root / 'config.env'
            envfile.write_text(f'APP_DATA_DIR={data}\nAPP_ENV=development\nAPP_HOST=127.0.0.1\n'
                               f'APP_PORT={port}\nMODEL=test/offline\nAPI_KEY=offline-fixture\n', encoding='utf8')
            env = os.environ.copy()
            for key in ('APP_DATA_DIR', 'APP_HOST', 'APP_PORT', 'APP_ENV', 'APP_ORIGINS'):
                env.pop(key, None)
            env['APP_ENV_FILE'] = str(envfile)
            def run(script):
                # Background children can inherit pipe handles; use files, not PIPE.
                with tempfile.TemporaryFile(mode='w+', encoding='utf8') as out, tempfile.TemporaryFile(mode='w+', encoding='utf8') as err:
                    result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                                             '-File', str(config.ROOT / script), '-Python', sys.executable],
                                            cwd=root, env=env, stdout=out, stderr=err, timeout=100)
                    out.seek(0);err.seek(0)
                    result.stdout=out.read();result.stderr=err.read()
                    return result
            try:
                started = run('Start-App.ps1')
                self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
                self.assertIn('App ready', started.stdout)
                self.assertTrue((data / f'app-process-{port}.json').is_file())
                duplicate = run('Start-App.ps1')
                self.assertEqual(duplicate.returncode, 0, duplicate.stderr)
                self.assertIn('already ready', duplicate.stdout)
            finally:
                stopped = run('Stop-App.ps1')
            self.assertEqual(stopped.returncode, 0, stopped.stderr)
            self.assertFalse((data / f'app-process-{port}.json').exists())
            self.assertIn('already stopped', run('Stop-App.ps1').stdout)
            missing = root / 'missing'
            env['APP_DATA_DIR'] = str(missing)
            failed = run('Start-App.ps1')
            self.assertNotEqual(failed.returncode, 0)
            self.assertFalse(missing.exists())
            with socket.socket() as occupied:
                occupied.bind(('127.0.0.1', port));occupied.listen()
                env['APP_DATA_DIR'] = str(data)
                self.assertNotEqual(run('Start-App.ps1').returncode, 0)
                self.assertNotEqual(run('Stop-App.ps1').returncode, 0)


if __name__ == '__main__':
    unittest.main()