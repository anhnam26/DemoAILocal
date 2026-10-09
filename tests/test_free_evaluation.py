import unittest
from tools.evaluate_free_chat import MODEL,ENDPOINT,guard_payload,validate_catalog,fixture
from cyberant.document_extractors import extract


class FreeEvaluationTests(unittest.TestCase):
    def test_free_price_must_be_explicit(self):
        valid={'id':MODEL,'pricing':{'prompt':'0','completion':'0'}}
        self.assertEqual(validate_catalog([valid],MODEL)['id'],MODEL)
        for entry in ({'id':MODEL},{**valid,'pricing':{'prompt':'0','completion':'0.001'}}):
            with self.assertRaises(ValueError):validate_catalog([entry],MODEL)
        with self.assertRaises(ValueError):validate_catalog([valid],'other/paid')

    def test_request_guard_no_paid_fallback_or_plugins(self):
        payload={'model':MODEL,'max_tokens':16000}
        guard_payload(ENDPOINT,payload,23)
        self.assertEqual(payload['provider']['max_price'],{'prompt':0,'completion':0})
        self.assertFalse(payload['provider']['allow_fallbacks'])
        for extra in ({'plugins':[]},{'models':[]},{'tools':[]},{'model':'paid'},{'max_tokens':16001}):
            with self.subTest(extra=extra),self.assertRaises(ValueError):guard_payload(ENDPOINT,dict(model=MODEL,max_tokens=100)|extra,0)
        with self.assertRaises(ValueError):guard_payload(ENDPOINT,payload,24)
        with self.assertRaises(ValueError):guard_payload('https://elsewhere.invalid',payload,0)

    def test_synthetic_answer_keys(self):
        name,data=fixture('sheets');result=extract(data,name)
        self.assertEqual(len(result['units']),2)
        for unit in result['units']:self.assertIn('B1: 6',unit['body'])
        name,data=fixture('pdf');result=extract(data,name)
        self.assertEqual(len(result['units']),35);self.assertIn('PDF-END-9137',result['units'][-1]['body'])
        name,data=fixture('long');self.assertIn('CYBERANT-END-7319',str(extract(data,name)))


if __name__=='__main__':unittest.main()