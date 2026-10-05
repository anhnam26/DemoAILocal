"""Bounded memory tests; no runtime data or provider calls."""
import hashlib,json,sqlite3,unittest
from contextlib import contextmanager
from fastapi import HTTPException
from cyberant import conversations,rag,quality_feedback

class MemoryTests(unittest.TestCase):
    def test_pairs_order_budget_and_topic_change(self):
        history=[dict(chat_id=i,question=f'VLAN thông số {i}',answer=f'Đáp án {i}',sources=[]) for i in range(10)]
        diagnostics={}
        messages,_,size=rag.pack('Giải thích ý thứ hai',[],8000,diagnostics=diagnostics,history=history)
        self.assertTrue(diagnostics['history_sent'])
        self.assertEqual(messages[1]['role'],'user');self.assertEqual(messages[2]['role'],'assistant')
        self.assertIn('Đáp án',messages[2]['content']);self.assertLessEqual(size,8000)
        self.assertEqual(rag.followup('DNS là gì?','VLAN là gì?'),'DNS là gì?')
        self.assertIn('Chủ đề trước',rag.followup('Giải thích phần 2','VLAN là gì?'))
        huge=[dict(chat_id=1,question='Q',answer='x'*20000)]
        self.assertEqual(rag.select_history('Q',huge,1000),[])

    def test_owner_conversation_and_revoked_digest(self):
        db=sqlite3.connect(':memory:');self.addCleanup(db.close);db.row_factory=sqlite3.Row
        db.executescript('CREATE TABLE conversations(id TEXT,user_id TEXT); CREATE TABLE chats(id INTEGER,conversation_id TEXT,user_id TEXT,question TEXT,result TEXT);')
        db.executemany('INSERT INTO conversations VALUES(?,?)',[('a','u'),('b','u'),('c','other')])
        digest=hashlib.sha256(b'valid').hexdigest()
        for i,cv,owner,source in [(1,'a','u',[]),(2,'b','u',[]),(3,'c','other',[]),(4,'a','u',[dict(id='D',source_digest='old')]),(5,'a','u',[dict(id='D',source_digest=digest)])]:
            db.execute('INSERT INTO chats VALUES(?,?,?,?,?)',(i,cv,owner,'question',json.dumps(dict(answer='answer',sources=source))))
        @contextmanager
        def connect():yield db
        items=conversations.context(connect,dict(id='u'),'a',[dict(id='D',body='valid')])
        self.assertEqual([i['chat_id'] for i in items],[1,5])
        db.execute('INSERT INTO chats VALUES(?,?,?,?,?)',(6,'a','u','summary',json.dumps(dict(answer='old derived answer',sources=[],context_sources=[dict(id='D',source_digest='old')]))))
        items=conversations.context(connect,dict(id='u'),'a',[dict(id='D',body='valid')])
        self.assertEqual([i['chat_id'] for i in items],[1,5])
        with self.assertRaises(HTTPException):conversations.context(connect,dict(id='u'),'c',[])

    def test_web_history_mapping_and_feedback_dependencies(self):
        db=sqlite3.connect(':memory:');self.addCleanup(db.close);db.row_factory=sqlite3.Row
        db.executescript('CREATE TABLE conversations(id TEXT,user_id TEXT); CREATE TABLE chats(id INTEGER,conversation_id TEXT,user_id TEXT,question TEXT,result TEXT,ts TEXT); CREATE TABLE users(id TEXT,username TEXT,name TEXT);')
        db.execute("INSERT INTO conversations VALUES('a','u')")
        db.execute("INSERT INTO users VALUES('u','fixture','Fixture')")
        prior=dict(answer='Old fact [WEB-1].',sources=[],context_sources=[dict(id='D',source_digest=hashlib.sha256(b'valid').hexdigest())],
                   web_sources=[dict(id='WEB-1',url='https://docs.example.com/old',retrieved_at='2026-10-01')])
        db.execute('INSERT INTO chats VALUES(?,?,?,?,?,?)',(1,'a','u','Q',json.dumps(prior),'now'))
        @contextmanager
        def connect():yield db
        history=conversations.context(connect,dict(id='u'),'a',[dict(id='D',body='valid')])
        self.assertNotIn('[WEB-1]',history[0]['answer']);self.assertIn('https://docs.example.com/old',history[0]['answer'])
        self.assertIn('chưa tra cứu lại',history[0]['answer'])
        snap=quality_feedback.snapshot(db,db.execute('SELECT * FROM chats').fetchone())
        self.assertEqual(snap['context_sources'],prior['context_sources']);self.assertEqual(snap['web_sources'],prior['web_sources'])
        redacted=quality_feedback.safe_snapshot(snap,{})
        self.assertTrue(redacted['source_redacted']);self.assertEqual(redacted['web_sources'],[])

if __name__=='__main__':unittest.main()