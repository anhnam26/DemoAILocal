import json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
from cyberant import attachments,conversations,operations,storage,document_extractors


class Attachments(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.data=self.root/'data'
        self.patch=patch('cyberant.config.env',return_value={'MODEL':'test','APP_DATA_DIR':str(self.data),'BOOTSTRAP_ADMIN_PASSWORD':'Fixture-password-12345'})
        self.patch.start();self.addCleanup(self.patch.stop)
        operations.initialize(self.data);self.connect=lambda:storage.connect(self.data)
        with self.connect() as c:
            self.u=dict(c.execute('SELECT * FROM users').fetchone());self.u['token']='fixture'
        self.now=lambda:'2026-10-09T00:00:00+00:00'
        self.cv=conversations.create(self.connect,self.u,self.now)

    def test_ownership_backup_restore_delete(self):
        raw=b'Switch quantity: 2';parsed=document_extractors.extract(raw,'bom.txt')
        id=attachments.save(self.connect,self.u,self.cv,'bom.txt',raw,parsed,self.now)
        self.assertEqual(attachments.listing(self.connect,self.u,self.cv)[0]['id'],id)
        docs=attachments.documents(self.connect,self.u,self.cv)
        self.assertEqual(docs[0]['body'],raw.decode());self.assertTrue(docs[0]['id'].startswith(id))
        with self.assertRaises(HTTPException):attachments.documents(self.connect,{'id':'other'},self.cv)
        cv2=conversations.create(self.connect,self.u,self.now)
        self.assertEqual(attachments.documents(self.connect,self.u,cv2),[])
        backup=self.root/'backup';restored=self.root/'restore'
        operations.backup(self.data,backup);operations.restore(backup,restored)
        with self.connect() as c,storage.connect(restored) as r:
            self.assertEqual(storage.digest_table(c,'attachments'),storage.digest_table(r,'attachments'))
        attachments.delete(self.connect,self.u,self.cv,id)
        self.assertEqual(attachments.documents(self.connect,self.u,self.cv),[])

    def test_explicit_upgrade_preserves_source(self):
        with self.connect() as c:
            c.execute('DROP TABLE attachments');c.execute('DROP TABLE attachment_schema')
            before=storage.digest_table(c,'docs');self.assertFalse(attachments.available(c))
            with self.assertRaises(HTTPException):attachments.require(c)
        target=self.root/'upgraded';operations.upgrade_attachments(self.data,target)
        with self.connect() as c,storage.connect(target) as n:
            self.assertFalse(attachments.available(c));self.assertTrue(attachments.available(n))
            self.assertEqual(before,storage.digest_table(n,'docs'))
        self.assertFalse((target/'backup.json').exists())
        with self.assertRaises(ValueError):operations.upgrade_attachments(self.data,target)

    def test_count_limit(self):
        parsed=document_extractors.extract(b'Test','a.txt')
        for i in range(10):attachments.save(self.connect,self.u,self.cv,'a.txt',b'Test',parsed,self.now)
        with self.assertRaises(HTTPException) as ctx:attachments.save(self.connect,self.u,self.cv,'a.txt',b'Test',parsed,self.now)
        self.assertEqual(ctx.exception.status_code,413)