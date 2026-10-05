"""Bulk acceptance keeps facts/retirement intact and persists through sync."""
import copy
import json
import sqlite3
import tempfile
import unittest
from cyberant import sync_knowledge
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


if __name__=='__main__':unittest.main()