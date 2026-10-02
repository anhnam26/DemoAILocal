"""Offline tunnel boundary tests, never opens public access."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
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