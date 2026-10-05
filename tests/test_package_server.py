"""Release allowlist, hostile paths and extracted runtime smoke checks."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from tools import package_server as release


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='cyberant-release-')
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.root=self.base/'source'
        for path in release.release_files():
            target=self.root/path.relative_to(release.ROOT)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)

    def test_allowlist_and_extracted_runtime(self):
        for relative in ('static/secret.env','static/junk.js','cyberant/demo.py','knowledge/evaluation_services.json','data/auth.sqlite3','.env'):
            path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('not a release file')
        archive=self.base/'release.zip';count=release.package(archive,self.root)
        with zipfile.ZipFile(archive) as z:
            names=z.namelist();self.assertEqual(len(names),count)
            self.assertNotIn('.env',names);self.assertNotIn('static/junk.js',names)
            self.assertNotIn('cyberant/demo.py',names);self.assertNotIn('knowledge/evaluation_services.json',names)
            self.assertFalse(any(n.startswith(('data/','tests/','tools/')) for n in names))
            extracted=self.base/'extracted';z.extractall(extracted)
        env=os.environ.copy()
        for key in list(env):
            if key.startswith(('APP_','MODEL','OPENROUTER_','BOOTSTRAP_')):env.pop(key,None)
        env.update(APP_DATA_DIR=str(self.base/'runtime'),APP_ENV='development',MODEL='test/offline',
                   BOOTSTRAP_ADMIN_PASSWORD='Offline-release-password',PYTHONDONTWRITEBYTECODE='1')
        for arguments in (['-m','cyberant.operations','init','--target',env['APP_DATA_DIR']],
                          ['-m','cyberant.operations','check'],['main.py','--help']):
            result=subprocess.run([sys.executable,'-B',*arguments],cwd=extracted,env=env,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stderr)
        code="from fastapi.testclient import TestClient;from cyberant.app import app\nwith TestClient(app) as c:\n assert c.get('/api/ready').json()['status']=='ready'\n r=c.post('/api/login',json={'username':'admin','password':'Offline-release-password'});assert r.status_code==200,r.text\n assert c.get('/').status_code==200\n assert c.get('/api/conversations').status_code==200\n"
        result=subprocess.run([sys.executable,'-B','-c',code],cwd=extracted,env=env,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr)
        with self.assertRaises(ValueError):release.package(archive,self.root)

    def test_checksum_missing_extra_and_escape(self):
        manifest=self.root/'knowledge/manifest.json';original=manifest.read_text(encoding='utf8')
        data=json.loads(original);path=self.root/'knowledge'/data['documents'][0]['path']
        raw=path.read_bytes();path.write_bytes(raw+b' ')
        with self.assertRaisesRegex(ValueError,'checksum'):release.release_files(self.root)
        path.write_bytes(raw)
        extra=self.root/'knowledge/documents/extra.json';extra.write_text('{}')
        with self.assertRaisesRegex(ValueError,'cover'):release.release_files(self.root)
        extra.unlink()
        data['documents'][0]['path']='documents/../../.env'
        manifest.write_text(json.dumps(data),encoding='utf8')
        with self.assertRaises(ValueError):release.release_files(self.root)
        manifest.write_text(original,encoding='utf8')
        (self.root/'static/app.js').unlink()
        with self.assertRaisesRegex(ValueError,'Missing'):release.release_files(self.root)

    def test_symlink_rejected(self):
        path=self.root/'static/app.js';path.unlink()
        target=self.base/'outside.js';target.write_text('outside')
        try:path.symlink_to(target)
        except OSError as exc:self.skipTest('Symlink creation unavailable: '+str(exc))
        with self.assertRaisesRegex(ValueError,'Symlink'):release.release_files(self.root)

    def test_symlink_parent_guard_without_os_privilege(self):
        original=Path.is_symlink
        with patch.object(Path,'is_symlink',lambda path: path==self.root/'static' or original(path)):
            with self.assertRaisesRegex(ValueError,'Symlink'):release.release_files(self.root)


if __name__=='__main__':unittest.main()