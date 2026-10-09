"""Isolated API regressions; provider is always replaced, no network calls."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from cyberant import operations,rag,attachments


class ChatEvidenceIntegrity(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='cyberant-integrity-');self.addCleanup(self.temp.cleanup)
        values=dict(APP_DATA_DIR=str(Path(self.temp.name)/'runtime'),APP_ENV='development',
                    APP_ORIGINS='http://testserver',BOOTSTRAP_ADMIN_PASSWORD='Offline-evidence-password',
                    MODEL='test/offline',API_KEY='never-sent',RAG_TOP_K='2',WEB_SEARCH_ENABLED='false',DEFAULT_MONTHLY_TOKENS='10000000')
        config_patch=patch('cyberant.config.env',return_value=values);config_patch.start();self.addCleanup(config_patch.stop)
        operations.initialize(Path(self.temp.name)/'runtime')
        from cyberant import app
        self.module=app
        self.client=TestClient(app.create_app());self.client.__enter__();self.addCleanup(self.client.__exit__,None,None,None)
        self.client.post('/api/login',json=dict(username='admin',password='Offline-evidence-password')).raise_for_status()
        self.cv=self.client.post('/api/conversations').json()['id']
        with app.connect() as c:self.u=dict(c.execute("SELECT * FROM users WHERE username='admin'").fetchone())

    def save(self,units):
        return attachments.save(self.module.connect,self.u,self.cv,'fixture.txt',b'synthetic',dict(units=units,warnings=[]),self.module.now)

    def ask(self,question,answer):
        async def complete(messages,settings,max_tokens):
            self.sent=messages
            return answer,dict(prompt_tokens=10,completion_tokens=10,total_tokens=20),'stop'
        with patch('cyberant.model_provider.complete',side_effect=complete):
            response=self.client.post('/api/chat',json=dict(question=question,conversation_id=self.cv))
        self.assertEqual(response.status_code,200,response.text);return response.json()

    def test_unicode_citations_still_validate_unknown_ids(self):
        id=self.save([dict(location='line 1',body='Quantity: 7')])+'-1'
        result=self.ask('Đọc file đính kèm',f'Quantity 7 【{id}】')
        self.assertEqual(result['citation_status'],'ids_valid_not_entailment_checked')
        self.assertIn('['+id+']',result['answer'])
        invalid=self.ask('Đọc file đính kèm',f'Quantity 7 【FAKE-999】')
        self.assertEqual(invalid['citation_status'],'invalid')
        unicode_dash=self.ask('Đọc file đính kèm','Quantity 7 ['+id.replace('-','‑')+']')
        self.assertEqual(unicode_dash['citation_status'],'ids_valid_not_entailment_checked')
        invalid_dash=self.ask('Đọc file đính kèm','Quantity 7 [FAKE‑999]')
        self.assertEqual(invalid_dash['citation_status'],'invalid')
        positional=self.ask('Đọc file đính kèm',f'Quantity 7 【{id}·Dòng 1】')
        self.assertEqual(positional['citation_status'],'ids_valid_not_entailment_checked')
        self.assertIn('Dòng 1',positional['answer'])

    def test_prompt_requires_safe_checks_and_exact_citation_format(self):
        self.assertIn('Không hướng dẫn cố tình gán IP đang được dùng',rag.SYSTEM)
        self.assertIn('luôn đặt trong ngoặc vuông []',rag.SYSTEM)
        self.assertIn('đề xuất cần xác nhận',rag.SYSTEM)

    def test_company_partial_model_context_has_visible_warning(self):
        result=self.ask('Liệt kê toàn bộ SOW BOM dịch vụ công ty','Bản tóm tắt cần kiểm tra')
        coverage=result['artifact_coverage']
        self.assertGreater(coverage['available'],coverage['sent_to_model'])
        self.assertIn('**Phạm vi SOW/BOM:**',result['answer'])
        self.assertIn('chưa thể coi là đầy đủ',result['answer'])

    def test_distinct_file_locations_not_deduplicated(self):
        id=self.save([dict(location='North A1:B1',body='Quantity | 6'),dict(location='South A1:B1',body='Quantity | 6')])
        result=self.ask('Tổng Quantity của tất cả sheet trong file?',f'12 [{id}-1] [{id}-2]')
        self.assertEqual(result['file_coverage'],dict(available_units=2,sent_units=2))
        self.assertIn('South A1:B1',str(self.sent))

    def test_uncited_file_dependency_revoked_in_history(self):
        id=self.save([dict(location='line 1',body='Private synthetic code: SECRET-7319')])
        self.ask('Đọc mã trong file','Mã là SECRET-7319')
        self.client.delete(f'/api/conversations/{self.cv}/attachments/{id}').raise_for_status()
        detail=self.client.get('/api/conversations/'+self.cv).json()
        self.assertIn('Nguồn đã thay đổi',detail['messages'][0]['answer'])
        self.ask('Tiếp tục ở trên','Không còn file')
        self.assertNotIn('SECRET-7319',str(self.sent))

    def test_followup_does_not_apply_retrieval_cap_to_all_files(self):
        units=[dict(location=f'line {i}',body=f'Unit {i}: reference for fixture') for i in range(5)]
        id=self.save(units)
        self.ask('Đọc file đính kèm',f'File [{id}-1]')
        result=self.ask('Tiếp tục đọc file ở trên',f'File [{id}-5]')
        self.assertEqual(result['file_coverage'],dict(available_units=5,sent_units=5))

    def test_large_file_technical_route_keeps_matching_unit(self):
        units=[dict(location=f'line {i}',body=f'Unrelated preparation reference {i} '+('x '*1800)) for i in range(35)]
        units.append(dict(location='last line',body='FortiGate mã xác nhận triển khai CYBERANT-END-7319'))
        id=self.save(units)
        result=self.ask('Cấu hình FortiGate: mã xác nhận triển khai trong file đính kèm là gì?',f'CYBERANT-END-7319 [{id}-36]')
        self.assertIn('CYBERANT-END-7319',str(self.sent))
        self.assertGreater(result['file_coverage']['sent_units'],0)
        self.assertEqual(result['citation_status'],'ids_valid_not_entailment_checked')


if __name__=='__main__':unittest.main()