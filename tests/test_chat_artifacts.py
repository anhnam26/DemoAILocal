"""Complete allowed records, independent of model output and facet coverage."""
import unittest
from cyberant import rag,service_evidence,sync_knowledge
from tools.audit_service_sources import evaluate
import json
from pathlib import Path


class Artifacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.docs=sync_knowledge.load()

    def test_migration_not_firewall_profile(self):
        q='Quy trình chuyển đổi cấu hình FortiGate, tổng giờ công?'
        self.assertIsNone(rag.configuration(q))
        found,_=rag.retrieve(q,self.docs,6)
        self.assertTrue({'ND-94154164F98B2E2E4FCA','ND-47781DEDABEDD4795BA4'}<={d['id'] for d in found})

    def test_full_sow_and_company(self):
        q='Cho tôi toàn bộ SOW chuyển đổi cấu hình FortiGate'
        items=service_evidence.artifacts(q,rag.intent(q),self.docs)
        expected={d['id'] for d in self.docs if service_evidence.service_id(d)=='configuration_migration' and d.get('data_type') in ('service_sow','migration_sow')}
        self.assertEqual(len(expected),21)
        self.assertTrue(expected<={d['id'] for d in items})
        q='Liệt kê tất cả SOW và BOM của công ty'
        items=service_evidence.artifacts(q,rag.intent(q),self.docs)
        self.assertIn('bom_rules',{d.get('data_type') for d in items})
        self.assertNotIn('glossary',{d.get('data_type') for d in items})
        self.assertEqual(service_evidence.artifacts(q,rag.intent(q),[]),[])

    def test_offline_evaluation(self):
        cases=json.loads((Path(__file__).resolve().parents[1]/'knowledge/evaluation_services.json').read_text(encoding='utf8'))['cases']
        result=evaluate(cases,self.docs)
        self.assertEqual(result['passed'],result['cases'])