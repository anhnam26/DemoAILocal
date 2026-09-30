import re
import app,model_provider,token_usage
from test_app import isolated_db,client

def test_abstention_without_citation_is_not_replaced(monkeypatch):
    async def reply(*args):return 'Kho tri thức chưa có đủ căn cứ để trả lời câu hỏi này.',{'prompt_tokens':50,'completion_tokens':20},'stop'
    monkeypatch.setattr(model_provider,'complete',reply)
    r=client().post('/api/chat',json={'question':'DNS là gì?'}).json()
    assert r['mode']=='Thiếu căn cứ' and r['citation_status']=='abstained'
    assert r['sources']==[] and not r['citations_verified']
    assert r['finish_reason']=='stop' and r['usage']['completion_tokens']==20

def test_length_is_saved_and_reported_without_retry(monkeypatch):
    calls=[]
    async def reply(messages,cfg,limit):
        calls.append(limit);id=re.findall(r'\[([A-Z0-9-]+)\]',messages[-1]['content'])[0]
        return 'DNS ['+id+']',{'prompt_tokens':100,'completion_tokens':limit},'length'
    monkeypatch.setattr(model_provider,'complete',reply)
    c=client();r=c.post('/api/chat',json={'question':'DNS là gì?'}).json()
    assert len(calls)==1 and r['finish_reason']=='length' and r['needs_review']
    assert 'chạm giới hạn' in r['answer'] and r['output_token_limit']==calls[0]
    assert r['citation_status']=='ids_valid_not_entailment_checked' and not r['grounding_verified']
    saved=c.get('/api/conversations/'+r['conversation_id']).json()['messages'][-1]
    assert saved['finish_reason']=='length'

def test_chat_does_not_silently_squeeze_output_near_quota(monkeypatch):
    c=client();u=c.get('/api/me').json()
    docs=app.docs_for();found,_=app.rag.retrieve('DNS là gì?',docs)
    budget,output=app.rag.budgets('DNS là gì?',18000,2400)
    _,_,estimated=app.rag.pack('DNS là gì?',found,budget)
    with app.connect() as db:db.execute('UPDATE users SET monthly_token_limit=? WHERE id=?',(estimated+output-1,u['id']))
    async def forbidden(*args):raise AssertionError('Should block before dispatch')
    monkeypatch.setattr(model_provider,'complete',forbidden)
    response=c.post('/api/chat',json={'question':'DNS là gì?'})
    assert response.status_code==429
    assert token_usage.summary(app.connect,u['id'])['reserved_tokens']==0
