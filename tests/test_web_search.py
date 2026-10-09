"""Public-query privacy, evidence validation and OpenRouter payload offline."""
import asyncio,unittest,tempfile,sqlite3
from pathlib import Path
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import httpx
from cyberant import model_provider,rag,web_search

class WebTests(unittest.TestCase):
    def test_disabled_by_default_and_approval_required(self):
        for values in ({},{'WEB_SEARCH_ENABLED':'true'},{'WEB_SEARCH_PROVIDER_APPROVED':'true'}):
            with patch('cyberant.config.env',return_value=values):self.assertFalse(web_search.settings()['enabled'])
        with patch('cyberant.config.env',return_value={'WEB_SEARCH_ENABLED':'true','WEB_SEARCH_PROVIDER_APPROVED':'true','WEB_SEARCH_MAX_RESULTS':'10'}):
            self.assertTrue(web_search.settings()['enabled']);self.assertEqual(web_search.settings()['max_results'],3)
        for query in ('DNS password=abc','DNS https://example.com?token=abc','DNS client@example.com','DNS 10.1.2.3'):
            self.assertIsNone(web_search.public_query('DNS',query))

    def test_persistent_atomic_quotas_and_concurrency(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'audit.sqlite3'
            @contextmanager
            def connect():
                c=sqlite3.connect(path,timeout=10);c.row_factory=sqlite3.Row
                try:
                    c.execute('BEGIN IMMEDIATE')
                    yield c;c.commit()
                finally:c.close()
            with connect() as c:c.execute('CREATE TABLE audit(id INTEGER PRIMARY KEY,ts TEXT,action TEXT,role TEXT,detail TEXT)')
            cfg=dict(monthly=5,daily=3,per_user=2,parallel=1)
            with ThreadPoolExecutor(max_workers=8) as pool:
                ids=list(pool.map(lambda _:web_search.reserve(connect,'user',cfg),range(8)))
            accepted=[i for i in ids if i is not None];self.assertEqual(len(accepted),1)
            web_search.release(connect,accepted[0])
            second=web_search.reserve(connect,'user',cfg);self.assertIsNotNone(second);web_search.release(connect,second)
            self.assertIsNone(web_search.reserve(connect,'user',cfg))
            # Fresh connections/server-independent counts persist after lease release.
            third=web_search.reserve(connect,'other',cfg);self.assertIsNotNone(third);web_search.release(connect,third)
            self.assertIsNone(web_search.reserve(connect,'third',cfg))
            with connect() as c:
                self.assertEqual(c.execute("SELECT COUNT(*) FROM audit WHERE action='web_search_reserve'").fetchone()[0],3)
                self.assertNotIn('DNS',str(c.execute('SELECT detail FROM audit').fetchall()))

    def test_task_presentation_not_account_role(self):
        from cyberant import service_evidence
        for q,wanted in [('Soạn email cho khách hàng về DNS','sales'),('Debug VPN và rollback','engineering'),('DNS là gì?','general'),('Báo giá và triển khai VPN','general')]:
            self.assertEqual(service_evidence.audience(q),wanted)
        self.assertIn('không suy đoán nghề nghiệp',rag.system_prompt('DNS là gì?'))

    def test_public_query_never_sends_private_text(self):
        query=web_search.public_query('Cấu hình VPN Cisco cho khách hàng ACME, IP 10.20.1.2, secret=ABC')
        self.assertEqual(query,'vpn cisco official documentation overview')
        self.assertNotIn('ACME',query);self.assertNotIn('10.20',query);self.assertNotIn('ABC',query)
        self.assertIsNone(web_search.public_query('Thông tin dự án khách hàng ACME'))
        self.assertEqual(web_search.public_query('private chat','DNS official docs'),'DNS official docs')
        self.assertFalse(web_search.should_search('DNS là gì?',[]))
        self.assertFalse(web_search.should_search('Giải thích phần 2',[]))
        self.assertTrue(web_search.should_search('CVE FortiGate mới nhất',[]))
        self.assertFalse(web_search.should_search('Cấu hình DNS Server',[dict(id='D',title='DNS')]))
        self.assertTrue(web_search.should_search('Cấu hình DNS',[dict(id='D',title='DNS')]))

    def test_extractive_evidence_urls_and_budget(self):
        def annotation(url,content='Official excerpt'):
            return dict(type='url_citation',url_citation=dict(url=url,content=content,title='Documentation'))
        usage=dict(web_annotations=[annotation('https://docs.example.com/a'),annotation('https://docs.example.com/a'),
            annotation('http://unsafe.example/a'),annotation('https://127.0.0.1/a'),annotation('https://localhost/a'),
            annotation('https://x.example/a',None),annotation('https://user:pass@x.example/a'),annotation('https://docs.example.com/b')])
        evidence=web_search.evidence(usage,3)
        self.assertEqual(len(evidence),2)
        self.assertTrue(all(e['id'].startswith('WEB-') for e in evidence))
        self.assertNotEqual(evidence[0]['id'],web_search.evidence(usage,3)[0]['id'])
        self.assertFalse(web_search.safe_url('javascript:alert(1)'))
        self.assertEqual(web_search.evidence(dict(web_annotations=123),3),[])
        diagnostics={};messages,_,size=rag.pack('DNS là gì?',[],8000,diagnostics=diagnostics,web=evidence)
        self.assertIn(evidence[0]['id'],messages[-1]['content']);self.assertLessEqual(size,8000)
        self.assertEqual(diagnostics['web_sent'],[e['id'] for e in evidence])

    def test_public_identifiers_and_web_reserved_budget(self):
        query=web_search.public_query('FortiGate firmware 7.4.3 CVE-2026-12345 client SECRET 10.1.2.3')
        self.assertIn('version 7.4.3',query);self.assertIn('cve-2026-12345',query)
        self.assertNotIn('SECRET',query);self.assertNotIn('10.1.2.3',query)
        web=[dict(id='WEB-test',title='DNS',url='https://docs.example.com',body='evidence'*20)]
        docs=[dict(id='D',title='DNS',group='A',body='internal '*1000)]
        diagnostics={}
        _,_,size=rag.pack('DNS là gì?',docs,8000,diagnostics=diagnostics,web=web)
        self.assertEqual(diagnostics['web_sent'],['WEB-test']);self.assertLessEqual(size,8000)
        self.assertTrue(web_search.requires_evidence('Lệnh cấu hình firmware'))

    def test_malformed_provider_payload(self):
        real=httpx.AsyncClient
        for payload in ([],dict(usage=['bad'],choices=[]),dict(usage={'prompt_tokens':10},choices=[dict(message=dict(content=''))])):
            def client(**kwargs):return real(transport=httpx.MockTransport(lambda request:httpx.Response(200,json=payload)),**kwargs)
            with patch('cyberant.model_provider.httpx.AsyncClient',side_effect=client):
                with self.assertRaises(model_provider.InvalidCompletion):
                    asyncio.run(model_provider.complete([],dict(model='test',api_key='fake',url='https://openrouter.ai/api/v1'),100))

    def test_payload_and_annotations_without_network(self):
        seen=[]
        def handler(request):
            import json
            seen.append(json.loads(request.content))
            return httpx.Response(200,json=dict(id='g-test',usage=dict(prompt_tokens=10,completion_tokens=5,total_tokens=15),
                choices=[dict(message=dict(content='summary',annotations=[dict(type='url_citation',url_citation=dict(url='https://docs.example.com',content='excerpt'))]),finish_reason='stop')]))
        real=httpx.AsyncClient
        def client(**kwargs):return real(transport=httpx.MockTransport(handler),**kwargs)
        with patch('cyberant.model_provider.httpx.AsyncClient',side_effect=client):
            text,usage,finish=asyncio.run(model_provider.complete(web_search.messages('DNS documentation'),dict(model='test/model',api_key='fake',url='https://openrouter.ai/api/v1',web_lookup=True,web_max_results=2),500))
        self.assertEqual(seen[0]['plugins'],[dict(id='web',engine='exa',max_results=2)])
        self.assertEqual(text,'summary');self.assertEqual(len(web_search.evidence(usage,2)),1)
        self.assertEqual(finish,'stop')

    def test_usage_totals_do_not_invent_missing_cost(self):
        result=web_search.aggregate([dict(prompt_tokens=10,completion_tokens=5,total_tokens=15,cost=.01),dict(prompt_tokens=20,completion_tokens=5,total_tokens=25)])
        self.assertEqual(result['total_tokens'],40);self.assertNotIn('cost',result)

if __name__=='__main__':unittest.main()