"""Bounded memory tests; no runtime data or provider calls."""
import hashlib,json,sqlite3,unittest
from contextlib import contextmanager
from fastapi import HTTPException
from cyberant import conversations,rag

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

if __name__=='__main__':unittest.main()