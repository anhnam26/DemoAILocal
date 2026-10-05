"""Bulk acceptance keeps facts/retirement intact and persists through sync."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from cyberant import operations,runtime_lock,storage,sync_knowledge
from tools import accept_knowledge as acceptance
from tools.accept_knowledge import accepted


class AcceptanceTests(unittest.TestCase):
    def test_acceptance_does_not_verify_unknown_facts(self):
        d=dict(id='X',status='approved',body='CHƯA CÓ / CHƯA XÁC NHẬN / DEMO',
               review_status='draft_engineer_review',provenance={'review_status':'draft_engineer_review','source_row':2})
        original=copy.deepcopy(d);a=accepted(d,'2026-10-05','User approved knowledge use')
        self.assertEqual(d,original);self.assertEqual(a['body'],d['body'])
        self.assertEqual(a['review_status'],'accepted');self.assertEqual(a['provenance']['review_status'],'accepted')
        self.assertEqual(a['review_decision']['authority'],'user_request')
        self.assertEqual(accepted(a,'later','other'),a)
        self.assertEqual(accepted({**d,'status':'retired'},'now','approval')['status'],'retired')

    def test_corpus_all_accepted_and_no_missing_facts_rewritten(self):
        ds=sync_knowledge.load()
        self.assertEqual(len(ds),1200)
        self.assertFalse(any(d.get('review_status')=='draft_engineer_review' for d in ds))
        self.assertFalse(any(d.get('provenance',{}).get('review_status')=='draft_engineer_review' for d in ds))
        self.assertEqual(sum(d.get('review_status')=='accepted' for d in ds),1100)
        self.assertTrue(any('CHƯA CÓ' in d['body'] for d in ds))

    def test_sync_preserves_acceptance_retirement_and_upload(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/'test.sqlite3'
            from cyberant.storage import Connection
            def connect():return sqlite3.connect(db,factory=Connection)
            with connect() as c:
                c.execute('CREATE TABLE docs(id TEXT PRIMARY KEY,payload TEXT)')
                c.execute('CREATE TABLE source_sync(id TEXT PRIMARY KEY,digest TEXT)')
                c.execute('INSERT INTO docs VALUES(?,?)',('UPLOAD',json.dumps({'id':'UPLOAD'})))
            d=accepted(dict(id='X',status='approved',body='unknown',review_status='draft_engineer_review'),'now','user')
            sync_knowledge.synchronize(connect,[d])
            with connect() as c:
                raw={**d,'status':'retired'}
                c.execute('UPDATE docs SET payload=? WHERE id=?',(json.dumps(raw),'X'))
            sync_knowledge.synchronize(connect,[{**d,'version':'2'}])
            with connect() as c:
                saved=json.loads(c.execute('SELECT payload FROM docs WHERE id=?',('X',)).fetchone()[0])
                self.assertEqual(saved['status'],'retired');self.assertEqual(saved['review_status'],'accepted')
                self.assertIsNotNone(c.execute('SELECT id FROM docs WHERE id=?',('UPLOAD',)).fetchone())


class AcceptanceWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='cyberant-acceptance-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.runtime=self.root/'runtime'
        self.corpus=self.root/'knowledge';self.corpus.mkdir()
        self.manifest=self.corpus/'manifest.json'
        self.backup=self.root/'backup'
        self.documents=[sync_knowledge.document('DRAFT','Draft','CHƯA CÓ / DEMO','F'),
                        sync_knowledge.document('RETIRED','Retired','CHƯA XÁC NHẬN','F'),
                        sync_knowledge.document('REF','Reference','Stable guidance','F')]
        for d in self.documents[:2]:
            d.update(review_status='draft_engineer_review',provenance={'review_status':'draft_engineer_review','source_row':2})
        entries=[]
        for d in self.documents:
            path=self.corpus/'documents'/(d['id']+'.json')
            path.parent.mkdir(exist_ok=True)
            operations._write_json(path,d)
            entries.append(dict(id=d['id'],path=path.relative_to(self.corpus).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        operations._write_json(self.manifest,dict(version=1,documents=entries))
        values=dict(APP_DATA_DIR=str(self.runtime),APP_ENV='development',MODEL='test/offline',
                    BOOTSTRAP_ADMIN_PASSWORD='Offline-acceptance-password')
        self.patcher=patch('cyberant.config.env',return_value=values)
        self.patcher.start();self.addCleanup(self.patcher.stop)
        with patch('cyberant.sync_knowledge.load',return_value=self.documents):operations.initialize(self.runtime)
        with storage.connect(self.runtime) as c:
            c.execute('UPDATE docs SET payload=? WHERE id=?',(acceptance.encode({**self.documents[1],'status':'retired'}),'RETIRED'))
            c.execute('INSERT INTO docs VALUES(?,?)',('UPLOAD',acceptance.encode({**self.documents[0],'id':'UPLOAD'})))

    def snapshot(self):
        files={p.relative_to(self.corpus).as_posix():p.read_bytes() for p in self.corpus.rglob('*.json')}
        with storage.connect(self.runtime) as c:
            tables={table:storage.digest_table(c,table) for group in storage.STORES.values() for table in group}
        return files,tables

    def test_apply_backup_restore_and_idempotence(self):
        before=self.snapshot()
        self.assertEqual(acceptance.run(self.manifest,self.runtime),dict(source_drafts=2,runtime_drafts=3,runtime_only_drafts=1,applied=False))
        self.assertEqual(self.snapshot(),before)
        result=acceptance.run(self.manifest,self.runtime,self.backup,'Owner approved knowledge use')
        self.assertTrue(result['applied']);self.assertEqual(result['remaining_drafts'],0)
        old_docs=sync_knowledge.load(self.backup/'knowledge/manifest.json')
        new_docs,rows=acceptance.inventory(self.manifest,self.runtime)
        for old,new in zip(old_docs,new_docs):
            self.assertEqual(old['body'],new['body'])
        self.assertEqual(rows['RETIRED']['status'],'retired')
        self.assertEqual(rows['UPLOAD']['review_status'],'accepted')
        self.assertEqual(rows['REF'],self.documents[2])
        with storage.connect(self.backup/'runtime') as a,storage.connect(self.backup/'restore-check') as b:
            for table,digest in before[1].items():
                self.assertEqual(storage.digest_table(a,table),digest)
                if table!='sessions':self.assertEqual(storage.digest_table(b,table),digest)
        with storage.connect(self.runtime) as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM audit WHERE action='knowledge_acceptance'").fetchone()[0],1)
        saved=self.snapshot()
        self.assertFalse(acceptance.run(self.manifest,self.runtime,self.root/'unused','Again')['applied'])
        self.assertFalse((self.root/'unused').exists());self.assertEqual(self.snapshot(),saved)

    def test_manifest_write_failure_rolls_back_files_and_database(self):
        before=self.snapshot();write=operations._write_json
        def fail(path,value):
            write(path,value)
            if path==self.manifest:raise OSError('Injected manifest write failure')
        with patch('cyberant.operations._write_json',side_effect=fail):
            with self.assertRaisesRegex(OSError,'Injected'):
                acceptance.run(self.manifest,self.runtime,self.backup,'Owner approval')
        self.assertEqual(self.snapshot(),before)
        acceptance.inventory(self.manifest,self.runtime)
        lock=runtime_lock.acquire(self.runtime);lock.close()
        self.assertTrue((self.backup/'acceptance.json').is_file())

    def test_safety_guards_prevent_writes(self):
        before=self.snapshot()
        for backup,reason in ((self.backup,''),(self.corpus/'backup','Owner'),
                              (self.runtime/'backup','Owner'),(self.root,'Owner')):
            with self.subTest(backup=backup,reason=reason):
                with self.assertRaises(ValueError):acceptance.run(self.manifest,self.runtime,backup,reason)
        lock=runtime_lock.acquire(self.runtime)
        try:
            code="from tools.accept_knowledge import run\ntry:\n run("+repr(str(self.manifest))+","+repr(str(self.runtime))+","+repr(str(self.backup))+",'Owner')\nexcept RuntimeError:\n pass\nelse:\n raise AssertionError('Apply acquired another process lock')\n"
            result=subprocess.run([sys.executable,'-B','-c',code],cwd=acceptance.ROOT,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
        finally:lock.close()
        self.assertEqual(self.snapshot(),before);self.assertFalse(self.backup.exists())

    def test_divergence_and_sync_digest_refuse_apply(self):
        for field in ('payload','digest'):
            with self.subTest(field=field):
                with storage.connect(self.runtime) as c:
                    if field=='payload':c.execute('UPDATE docs SET payload=? WHERE id=?',(acceptance.encode({**self.documents[0],'body':'Edited locally'}),'DRAFT'))
                    else:c.execute('UPDATE source_sync SET digest=? WHERE id=?',('bad','DRAFT'))
                before=self.snapshot()
                with self.assertRaises(ValueError):acceptance.run(self.manifest,self.runtime,self.backup,'Owner')
                self.assertEqual(self.snapshot(),before);self.assertFalse(self.backup.exists())
                with storage.connect(self.runtime) as c:
                    c.execute('UPDATE docs SET payload=? WHERE id=?',(acceptance.encode(self.documents[0]),'DRAFT'))


if __name__=='__main__':unittest.main()