"""Provider failure classification/privacy and isolated API ledger checks; no network."""
import asyncio,json,subprocess,sys,textwrap,unittest
from unittest.mock import patch
import httpx
from cyberant import config,model_provider,provider_errors

SECRET='Bearer SECRET-key private-question private-response'

class ProviderErrorTests(unittest.TestCase):
    def test_classification_and_safe_log_reference(self):
        request=httpx.Request('POST','https://openrouter.ai/api/v1/chat/completions',headers={'Authorization':SECRET},content=SECRET)
        errors=[(httpx.ConnectError(SECRET,request=request),'connection_error',503),
                (httpx.ReadTimeout(SECRET,request=request),'http_timeout',504),
                (httpx.ConnectTimeout(SECRET,request=request),'http_timeout',504),
                (httpx.RemoteProtocolError(SECRET,request=request),'transport_error',503),
                (TimeoutError(SECRET),'deadline_exceeded',504),
                (json.JSONDecodeError(SECRET,SECRET,0),'invalid_json',503),
                (ValueError(SECRET),'invalid_response',503),
                (model_provider.InvalidCompletion({'secret':SECRET}),'empty_content',503),
                (model_provider.InvalidCompletion({},SECRET),'invalid_response',503)]
        for status in (400,401,402,403,404,422,429,500,502,503):
            response=httpx.Response(status,request=request,content=SECRET)
            errors.append((httpx.HTTPStatusError(SECRET,request=request,response=response),'http_status',503))
        references=set()
        for error,kind,code in errors:
            with self.subTest(kind=kind,error=type(error).__name__),self.assertLogs('cyberant.provider',level='WARNING') as logs:
                failure,detail=provider_errors.failure(error,'test/model','completion','fixture-usage',1.234)
            record=json.loads(detail)
            self.assertEqual(failure.status_code,code);self.assertEqual(record['kind'],kind)
            self.assertEqual(record['exception_type'],type(error).__name__)
            self.assertEqual(record['elapsed_seconds'],1.23)
            self.assertRegex(record['error_id'],r'^[a-f0-9]{16}$')
            self.assertIn(record['error_id'],failure.detail);self.assertIn(detail,logs.output[0])
            self.assertNotIn(SECRET,detail+failure.detail+''.join(logs.output))
            self.assertNotIn('openrouter.ai/api/',detail);references.add(record['error_id'])
        self.assertEqual(len(references),len(errors))
        with self.assertLogs('cyberant.provider',level='WARNING'):
            _,detail=provider_errors.failure(ValueError(SECRET),'model\n'+SECRET,'completion','fixture-usage',0)
        self.assertEqual(json.loads(detail)['model'],'invalid_model_id')

    def test_provider_payload_shapes_and_one_send(self):
        real=httpx.AsyncClient
        usage=dict(prompt_tokens=10,completion_tokens=5,total_tokens=15)
        cases=[(b'not JSON private-response',None),([], 'invalid_response'),
               ({'choices':[]},'invalid_response'),({'choices':[None]},'invalid_response'),
               ({'choices':['bad']},'invalid_response'),({'choices':[{'message':None}]},'invalid_response'),
               ({'choices':[{'message':{'content':None}}]},'invalid_response'),
               ({'choices':[{'message':{'content':['bad']}}]},'invalid_response'),
               ({'choices':[{'message':{'content':'  '}}]},'empty_content')]
        for payload,reason in cases:
            seen=[]
            if isinstance(payload,dict):payload=dict(payload,usage=usage,id='fixture-generation')
            def handler(request):
                seen.append(request)
                return httpx.Response(200,content=payload) if isinstance(payload,bytes) else httpx.Response(200,json=payload)
            def client(**kwargs):return real(transport=httpx.MockTransport(handler),**kwargs)
            with self.subTest(payload=payload),patch('cyberant.model_provider.httpx.AsyncClient',side_effect=client):
                with self.assertRaises(json.JSONDecodeError if reason is None else model_provider.InvalidCompletion) as caught:
                    asyncio.run(model_provider.complete([dict(role='user',content=SECRET)],dict(model='test/model',api_key='fake-key',url='https://openrouter.ai/api/v1'),100))
            self.assertEqual(len(seen),1)
            if reason is not None:
                self.assertEqual(caught.exception.reason,reason)
                if isinstance(payload,dict):self.assertEqual(caught.exception.usage['total_tokens'],15)

    def test_api_failures_preserve_usage_no_retry_and_recover_gate(self):
        # Keep app import out of the parent process, as required by browser tests.
        code=textwrap.dedent('''\
        import json,logging,tempfile
        from pathlib import Path
        from unittest.mock import patch
        import httpx
        from fastapi.testclient import TestClient
        from cyberant import operations,model_provider
        from cyberant.app import create_app,connect
        secret='SECRET-key private-question private-response'
        logs=[]
        class Capture(logging.Handler):
            def emit(self,record):logs.append(record.getMessage())
        logger=logging.getLogger('cyberant.provider');handler=Capture();logger.addHandler(handler)
        real=httpx.AsyncClient
        with tempfile.TemporaryDirectory(prefix='cyberant-provider-') as temp:
            data=Path(temp)/'data'
            values=dict(APP_ENV='development',APP_DATA_DIR=str(data),MODEL='test/model',
                        API_KEY=secret,BOOTSTRAP_ADMIN_PASSWORD='Offline-provider-password',WEB_SEARCH_ENABLED='0')
            with patch('cyberant.config.env',return_value=values):
                operations.initialize(data)
                with TestClient(create_app()) as client:
                    assert client.post('/api/login',json=dict(username='admin',password='Offline-provider-password')).status_code==200
                    cv=client.post('/api/conversations').json()['id']
                    cases=[('connect',503,'connection_error','uncertain'),
                           ('timeout',504,'http_timeout','uncertain'),
                           ('protocol',503,'transport_error','uncertain'),
                           ('json',503,'invalid_json','uncertain'),
                           ('empty',503,'empty_content','completed'),
                           ('shape',503,'invalid_response','completed'),
                           ('status401',503,'http_status','cancelled'),
                           ('status429',503,'http_status','cancelled'),
                           ('status503',503,'http_status','uncertain'),
                           ('deadline',504,'deadline_exceeded','uncertain')]
                    for case,status,kind,ledger_state in cases:
                        sent=[]
                        def respond(request):
                            sent.append(request)
                            if case=='connect':raise httpx.ConnectError(secret,request=request)
                            if case=='timeout':raise httpx.ReadTimeout(secret,request=request)
                            if case=='protocol':raise httpx.RemoteProtocolError(secret,request=request)
                            if case=='json':return httpx.Response(200,content=secret)
                            if case.startswith('status'):return httpx.Response(int(case[6:]),content=secret)
                            return httpx.Response(200,json=dict(id='fixture-gen',usage=dict(prompt_tokens=10,completion_tokens=5,total_tokens=15),
                                  choices=[dict(message=dict(content=''))] if case=='empty' else [None]))
                        def transport(**kwargs):return real(transport=httpx.MockTransport(respond),**kwargs)
                        async def deadline(*args):
                            sent.append('deadline');raise TimeoutError(secret)
                        target='cyberant.model_provider.complete' if case=='deadline' else 'cyberant.model_provider.httpx.AsyncClient'
                        with patch(target,side_effect=deadline if case=='deadline' else transport):
                            response=client.post('/api/chat',json=dict(question='DNS la gi? '+secret,conversation_id=cv))
                        assert response.status_code==status,(case,response.text)
                        assert len(sent)==1,(case,len(sent))
                        record=json.loads(logs[-1]);assert record['kind']==kind,(case,record)
                        assert record['error_id'] in response.json()['detail']
                        assert secret not in response.text+logs[-1]
                        with connect() as db:
                            row=db.execute('SELECT status,total_tokens FROM token_usage WHERE id=?',(record['usage_record_id'],)).fetchone()
                            assert row['status']==ledger_state,(case,dict(row))
                            if ledger_state=='completed':assert row['total_tokens']==15
                            audit=db.execute("SELECT detail FROM audit WHERE action='model_error' ORDER BY id DESC LIMIT 1").fetchone()[0]
                            assert json.loads(audit)==record
                            assert db.execute("SELECT COUNT(*) FROM token_usage WHERE status IN ('reserved','in_flight')").fetchone()[0]==0
                            assert db.execute('SELECT COUNT(*) FROM chats').fetchone()[0]==0
                    async def success(*args):return 'General answer',dict(prompt_tokens=10,completion_tokens=5,total_tokens=15),'stop'
                    with patch('cyberant.model_provider.complete',side_effect=success) as complete:
                        response=client.post('/api/chat',json=dict(question='DNS la gi?',conversation_id=cv))
                    assert response.status_code==200,response.text
                    assert complete.call_count==1
                    values['WEB_SEARCH_ENABLED']='1'
                    async def web_failure(*args):raise httpx.ConnectError(secret)
                    with patch('cyberant.model_provider.complete',side_effect=web_failure) as complete:
                        response=client.post('/api/chat',json=dict(question='DNS la gi?',web_query='DNS official documentation',conversation_id=cv))
                    assert response.status_code==503,response.text
                    assert complete.call_count==1
                    assert json.loads(logs[-1])['stage']=='web_lookup'
                    with connect() as db:
                        assert db.execute('SELECT COUNT(*) FROM chats').fetchone()[0]==1
                        assert db.execute("SELECT COUNT(*) FROM token_usage WHERE status IN ('reserved','in_flight')").fetchone()[0]==0
        logger.removeHandler(handler)
        print('10 failure scenarios and recovery passed; web failure isolated; temporary stores only')
        ''')
        result=subprocess.run([sys.executable,'-B','-c',code],cwd=config.ROOT,capture_output=True,text=True,timeout=120)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('10 failure scenarios and recovery passed',result.stdout)

if __name__=='__main__':unittest.main()