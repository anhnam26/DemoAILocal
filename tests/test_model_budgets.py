"""Open budgets and explicit reasoning without paid requests."""
import asyncio,json,unittest
from unittest.mock import patch
import httpx
from cyberant import model_provider,rag


class Budgets(unittest.TestCase):
    def test_defaults_caps_and_reasoning(self):
        with patch('cyberant.config.env',return_value={'MODEL':'test'}):
            s=model_provider.settings()
        self.assertEqual((s['input_budget'],s['output_budget'],s['top_k']),(192000,16000,48))
        self.assertEqual(rag.budgets('SOW BOM công ty',192000,16000),(192000,16000))
        self.assertEqual(s['reasoning'],{'exclude':True})
        self.assertEqual(model_provider.reasoning_settings({'RAG_REASONING':'enabled','RAG_REASONING_EFFORT':'medium'}),{'enabled':True,'exclude':True,'effort':'medium'})
        with self.assertRaises(ValueError):model_provider.reasoning_settings({'RAG_REASONING':'invalid'})
        with patch('cyberant.config.env',return_value={'MODEL':'test','RAG_MODEL_LIMITS':'{"test":{"context_tokens":32768,"output_tokens":8192}}'}):
            s=model_provider.settings()
        self.assertEqual(s['output_budget'],8192)
        self.assertEqual(s['input_budget'],23552)

    def test_payload_excludes_trace_and_optional_temperature(self):
        seen=[]
        def handler(req):
            seen.append(json.loads(req.content))
            return httpx.Response(200,json={'choices':[{'message':{'content':'Answer','reasoning':'private trace'},'finish_reason':'stop'}],'usage':{'prompt_tokens':10,'completion_tokens':20}})
        real=httpx.AsyncClient
        with patch('cyberant.model_provider.httpx.AsyncClient',side_effect=lambda **kw:real(transport=httpx.MockTransport(handler),**kw)):
            answer,_,_=asyncio.run(model_provider.complete([],{'api_key':'fixture','model':'test','url':'https://test.invalid','reasoning':{'enabled':True,'exclude':True}},16000))
        self.assertEqual(answer,'Answer')
        self.assertNotIn('temperature',seen[0])
        self.assertEqual(seen[0]['reasoning'],{'enabled':True,'exclude':True})