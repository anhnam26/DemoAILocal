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
            self.assertNotIn('cyberant/public_share.py',names);self.assertNotIn('docs/PUBLIC_SHARE.md',names)
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

    def private_fixture(self):
        from cyberant import operations,storage
        runtime=self.base/'runtime'
        values=dict(APP_DATA_DIR=str(runtime),APP_ENV='development',MODEL='test/offline',
                    BOOTSTRAP_ADMIN_PASSWORD='Offline-release-password')
        with patch('cyberant.config.env',return_value=values):operations.initialize(runtime)
        with storage.connect(runtime) as c:
            user=c.execute('SELECT id FROM users').fetchone()[0]
            c.execute('INSERT INTO sessions(token,profile,created,user_id) VALUES(?,?,?,?)',('old-session','admin',1,user))
        env=self.root/'.env'
        env.write_text('OPENROUTER_API_KEY=fake-offline-secret\nMODEL=test/offline\nAPP_ENV=development\n'
                       'APP_HOST=127.0.0.1\nAPP_DATA_DIR=D:\\old-machine\\data\n'
                       'export APP_BACKUP_DIR=D:\\old-machine\\backups\nRAG_OUTPUT_TOKENS=8000\n',encoding='utf8')
        return runtime,env

    def test_private_bundle_preserves_data_and_secret_without_reusing_sessions(self):
        from cyberant import storage
        runtime,env=self.private_fixture();original=env.read_bytes()
        archive=self.base/'private.zip'
        count=release.package_private(archive,runtime,env,self.root)
        extracted=self.base/'private-extracted'
        with zipfile.ZipFile(archive) as z:
            self.assertEqual(len(z.namelist()),count);self.assertIsNone(z.testzip())
            expected={p.relative_to(self.root).as_posix() for p in release.release_files(self.root)}
            private={'.env','data/layout.json'}|{'data/'+p.relative_to(runtime).as_posix() for p in storage.paths(runtime).values()}
            self.assertEqual(set(z.namelist()),expected|private)
            self.assertNotIn('cyberant/public_share.py',z.namelist());self.assertNotIn('docs/PUBLIC_SHARE.md',z.namelist())
            self.assertEqual(z.read('.env').decode('utf8'),release.portable_env(original.decode('utf8')))
            self.assertIn('OPENROUTER_API_KEY=fake-offline-secret',z.read('.env').decode('utf8'))
            self.assertEqual(z.getinfo('.env').external_attr>>16,0o100600)
            z.extractall(extracted)
        self.assertEqual(env.read_bytes(),original)
        storage.validate(extracted/'data',integrity=True)
        with storage.connect(runtime) as before,storage.connect(extracted/'data') as after:
            for group in storage.STORES.values():
                for table in group:
                    if table!='sessions':self.assertEqual(storage.digest_table(before,table),storage.digest_table(after,table),table)
            self.assertEqual(before.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],1)
            self.assertEqual(after.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],0)
        clean=os.environ.copy()
        for key in list(clean):
            if key.startswith(('APP_','MODEL','OPENROUTER_','BOOTSTRAP_')):clean.pop(key,None)
        code="from cyberant import config,model_provider;from pathlib import Path\nassert config.data_dir()==Path.cwd()/'data'\nassert model_provider.settings()['api_key']=='fake-offline-secret'\nfrom fastapi.testclient import TestClient\nfrom cyberant.app import app\nwith TestClient(app) as c:\n assert c.get('/api/ready').status_code==200\n assert c.post('/api/login',json={'username':'admin','password':'Offline-release-password'}).status_code==200\n assert c.get('/api/conversations').status_code==200\n"
        result=subprocess.run([sys.executable,'-B','-c',code],cwd=extracted,env=clean,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr)
        with self.assertRaises(ValueError):release.package_private(archive,runtime,env,self.root)

    def test_private_bundle_refuses_unsafe_paths_active_usage_and_other_process(self):
        from cyberant import runtime_lock,storage
        runtime,env=self.private_fixture();archive=self.base/'private.zip'
        with self.assertRaisesRegex(ValueError,'outside'):release.package_private(self.root/'bad.zip',runtime,env,self.root)
        with self.assertRaisesRegex(ValueError,'missing'):release.package_private(archive,runtime,self.base/'missing.env',self.root)
        lock=runtime_lock.acquire(runtime)
        try:
            code="from tools.package_server import package_private\ntry:\n package_private("+','.join(repr(str(p)) for p in (archive,runtime,env,self.root))+ ")\nexcept RuntimeError:\n pass\nelse:\n raise AssertionError('Other process lock was ignored')\n"
            result=subprocess.run([sys.executable,'-B','-c',code],cwd=release.ROOT,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
        finally:lock.close()
        with storage.connect(runtime) as c:
            c.execute("INSERT INTO token_usage(id,user_id,model,month,status,reserved_tokens,created,updated) VALUES('active','fixture','test/offline','2026-10','reserved',100,1,1)")
        with self.assertRaisesRegex(ValueError,'active'):release.package_private(archive,runtime,env,self.root)
        self.assertFalse(archive.exists())

    def test_portable_env_preserves_other_settings_and_adds_missing_paths(self):
        raw='# comment\nOPENROUTER_API_KEY=fake=value\nRAG_TOP_K=24\n'
        result=release.portable_env(raw)
        self.assertTrue(result.startswith(raw))
        self.assertIn('APP_DATA_DIR=data\n',result)
        self.assertIn('APP_BACKUP_DIR=../CyberAnt-private/backups\n',result)


if __name__=='__main__':unittest.main()