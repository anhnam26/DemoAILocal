"""LAN security and removed tunnel CLI; isolated stores, no provider generation."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
import main
from cyberant import config,operations
from cyberant.app import create_app


class LanServerTests(unittest.TestCase):
    def test_removed_share_options_fail_before_listener(self):
        for args in (['--share'],['--cloudflared','unused'],['--share-protocol','http2']):
            with self.subTest(args=args),patch('main.socket.create_server') as listen:
                with patch('cyberant.config.env',return_value={}),contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:main.main(args)
                self.assertEqual(error.exception.code,2);listen.assert_not_called()
        with patch('cyberant.config.env',return_value={}),contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as error:main.main(['--help'])
        self.assertEqual(error.exception.code,0)
        self.assertNotIn('--share',output.getvalue());self.assertNotIn('cloudflared',output.getvalue())

    def test_development_cannot_bind_lan(self):
        with patch('cyberant.config.env',return_value={'APP_ENV':'development'}),patch('main.socket.create_server') as listen:
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:main.main(['--host','192.168.1.100'])
            self.assertEqual(error.exception.code,1);listen.assert_not_called()

    def test_lan_origins_reject_public_and_wildcard(self):
        for origin in ('http://8.8.8.8:8088','http://example.com:8088','http://*.example.com','http://192.168.1.100:8088/path'):
            with self.subTest(origin=origin),patch('cyberant.config.env',return_value={'APP_ENV':'lan','APP_ORIGINS':origin}):
                with self.assertRaises(ValueError):config.security()

    def test_lan_login_host_origin_and_existing_data(self):
        with tempfile.TemporaryDirectory(prefix='cyberant-lan-') as temp:
            data=Path(temp)/'data'
            values=dict(APP_ENV='lan',APP_HOST='192.168.1.100',APP_PORT='8088',
                        APP_ORIGINS='http://192.168.1.100:8088',APP_DATA_DIR=str(data),
                        MODEL='test/offline',API_KEY='offline-fixture',BOOTSTRAP_ADMIN_PASSWORD='Offline-LAN-password')
            with patch('cyberant.config.env',return_value=values):
                operations.initialize(data)
                security=config.security()
                self.assertFalse(security['secure_cookie']);self.assertEqual(security['mode'],'lan')
                with TestClient(create_app(),base_url='http://192.168.1.100:8088') as client:
                    self.assertEqual(client.get('/api/ready').status_code,200)
                    self.assertEqual(client.get('/api/conversations').status_code,401)
                    self.assertEqual(client.get('/',headers={'host':'attacker.example'}).status_code,400)
                    self.assertEqual(client.post('/api/login',headers={'origin':'http://192.168.1.101:8088'},json={'username':'admin','password':'Offline-LAN-password'}).status_code,403)
                    login=client.post('/api/login',headers={'origin':values['APP_ORIGINS']},json={'username':'admin','password':'Offline-LAN-password'})
                    self.assertEqual(login.status_code,200)
                    self.assertIn('httponly',login.headers['set-cookie'].lower())
                    self.assertNotIn('; secure',login.headers['set-cookie'].lower())
                    self.assertEqual(client.get('/api/conversations').status_code,200)


if __name__=='__main__':unittest.main()