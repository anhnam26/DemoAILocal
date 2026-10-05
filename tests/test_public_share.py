"""Offline tunnel boundary tests, never opens public access."""
from pathlib import Path
import contextlib
import io
import os
import signal
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from unittest.mock import MagicMock, patch
import main
from cyberant import config, operations, public_share, storage


class PublicShareTests(unittest.TestCase):
    def test_rejects_non_linux_before_launch(self):
        with patch('cyberant.public_share.sys.platform','win32'):
            with self.assertRaisesRegex(ValueError,'Linux'):
                public_share.preflight(Path('.'),Path('.'),'must-not-launch')

    def test_exact_quick_tunnel_url_pattern(self):
        url='https://safe-random-url.trycloudflare.com'
        self.assertEqual(public_share.URL_PATTERN.search('Tunnel: '+url+' |').group(),url)
        self.assertIsNone(public_share.URL_PATTERN.search(url+'.attacker.example'))

    def test_validates_new_stores_and_requires_active_admin(self):
        with tempfile.TemporaryDirectory(prefix='cyberant-share-test-') as temp:
            root=Path(temp)/'runtime'
            values={'APP_DATA_DIR':str(root),'MODEL':'offline/test',
                    'BOOTSTRAP_ADMIN_PASSWORD':'Offline-password-only'}
            with patch('cyberant.config.env',return_value=values):
                operations.initialize(root)
                public_share.validate_database(root)
                with storage.connect(root) as c:
                    c.execute('UPDATE users SET active=0')
                with self.assertRaisesRegex(ValueError,'administrator'):
                    public_share.validate_database(root)

    def test_missing_binary_root_and_config_rejected_without_launch(self):
        with patch.object(public_share.sys,'platform','linux'),patch.object(public_share.os,'geteuid',return_value=0,create=True):
            with self.assertRaisesRegex(ValueError,'root'):public_share.preflight(Path('.'),Path('.'),'cloudflared')
        with patch.object(public_share.sys,'platform','linux'),patch.object(public_share.os,'geteuid',return_value=1000,create=True),patch('cyberant.public_share.shutil.which',return_value=None):
            with self.assertRaisesRegex(ValueError,'cloudflared not found'):public_share.preflight(Path('.'),Path('.'),'missing')
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(public_share.sys,'platform','linux'),patch.object(public_share.os,'geteuid',return_value=1000,create=True),patch('cyberant.public_share.shutil.which',return_value=sys.executable),patch('cyberant.config.env_path',return_value=Path(temp)/'missing.env'):
                with self.assertRaisesRegex(ValueError,'existing private'):public_share.preflight(Path('.'),Path(temp),'installed')

    def test_main_uses_env_port_and_loopback_only_for_share(self):
        values=dict(APP_ENV='development',APP_HOST='0.0.0.0',APP_PORT='9234',MODEL='test/offline')
        listener=MagicMock();lock=MagicMock();server=MagicMock(started=True)
        with patch('cyberant.config.env',return_value=values),patch('cyberant.public_share.preflight',return_value='installed') as preflight,patch('cyberant.public_share.validate_database') as validate,patch('cyberant.public_share.serve') as serve,patch('main.socket.create_server',return_value=listener) as listen,patch('cyberant.runtime_lock.acquire',return_value=lock),patch('cyberant.storage.validate'),patch('uvicorn.Server',return_value=server):
            main.main(['--share','--share-protocol','http2'])
        listen.assert_called_once_with(('127.0.0.1',9234),family=main.socket.AF_INET,backlog=2048)
        preflight.assert_called_once();validate.assert_called_once()
        serve.assert_called_once_with(server,listener,'installed',9234,'http2')
        listener.close.assert_called_once();lock.close.assert_called_once()

    def test_normal_mode_uses_config_host_and_port(self):
        values=dict(APP_ENV='lan',APP_HOST='192.168.1.50',APP_PORT='9234',APP_ORIGINS='http://192.168.1.50:9234',MODEL='test/offline')
        listener=MagicMock();lock=MagicMock();server=MagicMock(started=True)
        with patch('cyberant.config.env',return_value=values),patch('main.socket.create_server',return_value=listener) as listen,patch('cyberant.runtime_lock.acquire',return_value=lock),patch('cyberant.storage.validate'),patch('cyberant.public_share.preflight') as preflight,patch('uvicorn.Server',return_value=server),contextlib.redirect_stdout(io.StringIO()):
            main.main([])
        self.assertEqual(listen.call_args.args[0],('192.168.1.50',9234));preflight.assert_not_called()
        server.run.assert_called_once_with(sockets=[listener]);lock.close.assert_called_once()

    def test_duplicate_port_does_not_launch_tunnel_or_touch_database(self):
        with patch('cyberant.config.env',return_value={'APP_PORT':'9234','MODEL':'test/offline'}),patch('cyberant.public_share.preflight',return_value='installed'),patch('main.socket.create_server',side_effect=OSError('occupied')),patch('cyberant.public_share.serve') as serve,patch('cyberant.runtime_lock.acquire') as lock,contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):main.main(['--share'])
        serve.assert_not_called();lock.assert_not_called()

    def test_duplicate_data_lock_closes_listener_without_tunnel(self):
        listener=MagicMock()
        with patch('cyberant.config.env',return_value={'APP_PORT':'9234','MODEL':'test/offline'}),patch('cyberant.public_share.preflight',return_value='installed'),patch('main.socket.create_server',return_value=listener),patch('cyberant.runtime_lock.acquire',side_effect=RuntimeError('already running')),patch('cyberant.public_share.serve') as serve,contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):main.main(['--share'])
        listener.close.assert_called_once();serve.assert_not_called()

    def test_bash_preserves_active_environment_and_forwards_options(self):
        bash=Path('C:/Program Files/Git/bin/bash.exe') if os.name=='nt' else Path(shutil.which('bash') or '/missing')
        if not bash.is_file():self.skipTest('Bash unavailable')
        with tempfile.TemporaryDirectory(prefix='cyberant-bash-') as temp:
            root=Path(temp);binary=root/'bin/python';binary.parent.mkdir()
            binary.write_text('#!/bin/sh\nprintf "cwd=%s\\nconfig=%s\\n" "$PWD" "$APP_ENV_FILE"\nprintf "arg=%s\\n" "$@"\n',encoding='utf8')
            binary.chmod(0o700)
            environment=os.environ.copy();environment.pop('CONDA_ENV_NAME',None)
            environment.update(CONDA_PREFIX=root.as_posix(),APP_ENV_FILE='server-private.env')
            result=subprocess.run([str(bash),str(config.ROOT/'start.sh'),'--share','--share-protocol','http2','--port','9345'],cwd=root,env=environment,capture_output=True,text=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('config=server-private.env',result.stdout)
            self.assertIn('arg=--share\narg=--share-protocol\narg=http2\narg=--port\narg=9345',result.stdout)
            self.assertIn('TestSystem',result.stdout) if os.name=='nt' else self.assertIn(config.ROOT.name,result.stdout)

    def test_tunnel_command_filters_secrets_drains_logs_and_cleans_up(self):
        process=MagicMock();process.poll.return_value=None
        process.stdout=io.StringIO('secret raw credentials\nhttps://safe-test.trycloudflare.com |\nRegistered tunnel connection\n')
        with patch.dict(os.environ,{'API_KEY':'do-not-forward','APP_DATA_DIR':'private','TUNNEL_TOKEN':'secret-token'}),patch('cyberant.public_share.subprocess.Popen',return_value=process) as launch:
            tunnel=public_share.QuickTunnel('installed',9234,'http2')
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(tunnel.start(timeout=1),'https://safe-test.trycloudflare.com')
                tunnel.close()
        command=launch.call_args.args[0];environment=launch.call_args.kwargs['env']
        self.assertIn('http://127.0.0.1:9234',command);self.assertIn('http2',command)
        for key in ('API_KEY','APP_DATA_DIR','TUNNEL_TOKEN'):self.assertNotIn(key,environment)
        self.assertEqual(output.getvalue(),'');process.terminate.assert_called_once();self.assertTrue(process.stdout.closed)

    def test_tunnel_timeout_exit_cancel_and_kill_cleanup(self):
        for state in ('timeout','exit','cancel'):
            with self.subTest(state=state):
                process=MagicMock();process.stdout=io.StringIO('');process.poll.return_value=1 if state=='exit' else None
                tunnel=public_share.QuickTunnel('installed',9234)
                if state=='cancel':tunnel.cancelled.set()
                with patch('cyberant.public_share.subprocess.Popen',return_value=process):
                    with self.assertRaises(KeyboardInterrupt if state=='cancel' else RuntimeError):tunnel.start(timeout=0.01 if state=='timeout' else 1)
                if state=='timeout':process.wait.side_effect=[subprocess.TimeoutExpired('installed',10),0]
                tunnel.close()
                if state=='timeout':process.kill.assert_called_once()

    def test_signal_handlers_restored_on_start_failure(self):
        tunnel=public_share.QuickTunnel('installed',9234)
        with patch.object(signal,'SIGHUP',1,create=True),patch('cyberant.public_share.signal.signal',return_value='previous') as handler:
            with self.assertRaisesRegex(RuntimeError,'failure'):
                with tunnel:
                    tunnel._cancel(signal.SIGTERM,None)
                    self.assertTrue(tunnel.cancelled.is_set())
                    raise RuntimeError('failure')
        self.assertEqual(handler.call_count,6)
        self.assertTrue(all(call.args[1]=='previous' for call in handler.call_args_list[3:]))

    def test_config_file_relative_paths_and_explicit_overrides(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);envfile=root/'server.env'
            raw='APP_ENV=lan\nAPP_HOST=0.0.0.0\nAPP_PORT=9234\nAPP_ORIGINS=http://192.168.1.50:9234\nAPP_DATA_DIR=server-data\nAPP_BACKUP_DIR=../server-backups\nMODEL=test/offline\n'
            envfile.write_text(raw,encoding='utf8')
            with patch('cyberant.config.ROOT',root),patch.dict(os.environ,{'APP_ENV_FILE':'server.env'},clear=True):
                self.assertEqual(config.env()['APP_PORT'],'9234')
                self.assertEqual(config.env_path(),envfile)
                self.assertEqual(config.data_dir(),(root/'server-data').resolve())
                self.assertEqual(config.backup_dir(),(root/'../server-backups').resolve())
                self.assertEqual(config.security()['mode'],'lan')
                with patch.dict(os.environ,{'APP_PORT':'9345'}):self.assertEqual(config.env()['APP_PORT'],'9345')
            self.assertEqual(envfile.read_text(encoding='utf8'),raw)

    def test_app_startup_timeout_closes_tunnel_without_announcing(self):
        tunnel=MagicMock();tunnel.__enter__.return_value=tunnel
        tunnel.start.return_value='https://safe-test.trycloudflare.com'
        tunnel.cancelled=threading.Event();tunnel.process.poll.return_value=None
        server=MagicMock(started=False,should_exit=False)
        real_monotonic=time.monotonic
        def run(**kwargs):
            deadline=real_monotonic()+3
            while not server.should_exit and real_monotonic()<deadline:time.sleep(0.02)
            self.assertTrue(server.should_exit)
        server.run.side_effect=run
        with patch('cyberant.public_share.QuickTunnel',return_value=tunnel),patch('cyberant.public_share.time.monotonic',side_effect=[0,121]),patch.dict(os.environ,{},clear=True),contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaisesRegex(RuntimeError,'Sharing session failed'):public_share.serve(server,object(),'installed',9234,'auto')
        self.assertNotIn('Public URL:',output.getvalue());tunnel.close.assert_called_once()

    def test_serve_preserves_file_and_other_settings_restores_env_on_exit(self):
        for failure in (None,'start','app','dead','cancel','url'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temp:
                envfile=Path(temp)/'server.env'
                original=b'APP_ENV=development\nAPP_HOST=0.0.0.0\nAPP_PORT=9234\nAPI_KEY=offline-secret\nMODEL=test/offline\nAPP_DATA_DIR=data\n'
                envfile.write_bytes(original)
                tunnel=MagicMock();tunnel.__enter__.return_value=tunnel
                tunnel.start.return_value='https://safe-test.trycloudflare.com'
                tunnel.cancelled=threading.Event();tunnel.process.poll.return_value=1 if failure=='dead' else None
                if failure=='start':tunnel.start.side_effect=RuntimeError('start failed')
                if failure=='url':tunnel.start.return_value='https://safe-test.trycloudflare.com.attacker.example'
                if failure=='cancel':tunnel.cancelled.set()
                server=MagicMock(started=False,should_exit=False)
                def run(**kwargs):
                    values=config.env();security=config.security()
                    self.assertEqual(values['API_KEY'],'offline-secret');self.assertEqual(values['MODEL'],'test/offline')
                    self.assertEqual(values['APP_PORT'],'9234');self.assertEqual(values['APP_DATA_DIR'],'data')
                    self.assertEqual(security['origins'],[tunnel.start.return_value]);self.assertTrue(security['secure_cookie'])
                    self.assertEqual(security['hosts'],{'safe-test.trycloudflare.com'})
                    if failure=='app':raise RuntimeError('app failed')
                    if failure!='dead':server.started=True
                    deadline=time.monotonic()+2
                    while time.monotonic()<deadline and not server.should_exit:time.sleep(0.02)
                server.run.side_effect=run
                with patch.dict(os.environ,{'APP_ENV_FILE':str(envfile)},clear=True),patch('cyberant.public_share.QuickTunnel',return_value=tunnel),contextlib.redirect_stdout(io.StringIO()) as output:
                    before=dict(os.environ)
                    if failure:
                        with self.assertRaises(KeyboardInterrupt if failure=='cancel' else ValueError if failure=='url' else RuntimeError):public_share.serve(server,object(),'installed',9234,'auto')
                    else:public_share.serve(server,object(),'installed',9234,'auto')
                    self.assertEqual(dict(os.environ),before)
                    self.assertIsNone(config._public_share_origin)
                self.assertEqual(envfile.read_bytes(),original);tunnel.__exit__.assert_called_once()
                self.assertEqual('Public URL:' in output.getvalue(),failure is None)

    def test_https_auth_host_origin_and_secure_cookie_offline(self):
        code=textwrap.dedent('''\
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from cyberant import config,operations
        from cyberant.app import create_app
        with tempfile.TemporaryDirectory() as temp:
            origin='https://safe-test.trycloudflare.com'
            values=dict(APP_ENV='production',APP_ORIGINS=origin,APP_DATA_DIR=str(Path(temp)/'data'),MODEL='test/offline',API_KEY='offline',BOOTSTRAP_ADMIN_PASSWORD='Offline-share-password')
            with patch('cyberant.config.env',return_value=values),patch('cyberant.config._public_share_origin',origin):
                operations.initialize(Path(values['APP_DATA_DIR']))
                with TestClient(create_app(),base_url=origin) as client:
                    assert client.get('/api/conversations').status_code==401
                    assert client.get('/',headers={'host':'other.trycloudflare.com'}).status_code==400
                    assert client.get('/',headers={'host':'localhost'}).status_code==400
                    assert client.post('/api/login',headers={'origin':'https://other.trycloudflare.com'},json={'username':'admin','password':'Offline-share-password'}).status_code==403
                    response=client.post('/api/login',headers={'origin':origin},json={'username':'admin','password':'Offline-share-password'})
                    assert response.status_code==200
                    assert '; secure' in response.headers['set-cookie'].lower()
                    assert 'httponly' in response.headers['set-cookie'].lower()
                    assert client.get('/api/conversations').status_code==200
        ''')
        result=subprocess.run([sys.executable,'-B','-c',code],cwd=config.ROOT,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr)