"""Offline service evidence routing, prompts and atomic packing."""
import unittest
from cyberant import rag,service_evidence,sync_knowledge


class ServiceRagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.documents=sync_knowledge.load()

    def test_intents_multi_part_and_definitions(self):
        cases={'SOW BOM Managed Service':'sow_bom','Lập SOW dịch vụ RMA':'sow',
               'BOM FortiGate':'bom','BOM là gì?':'concept','SOW là gì?':'concept',
               'Quy trình migration FortiGate':'procedure'}
        for question,expected in cases.items():
            with self.subTest(question=question):self.assertEqual(rag.intent(question),expected)
        self.assertEqual(rag.budgets('SOW BOM Managed Service',9000,1200),(9000,1200))
        self.assertEqual(rag.budgets('BOM là gì?',18000,2400),(8000,1000))

    def test_service_resolution_and_legacy_links(self):
        self.assertEqual(service_evidence.resolve_services('Chuyển đổi cấu hình FortiGate, SOW'),['configuration_migration'])
        self.assertEqual(service_evidence.resolve_services('SOW RMA và Managed Service'),['managed_service','rma'])
        self.assertEqual(service_evidence.resolve_services('normal protocol'),[])
        for doc in self.documents:
            if doc.get('data_type')=='workflow':self.assertIsNotNone(service_evidence.service_id(doc))
            if doc.get('service')=='Managed Service.docx':
                self.assertEqual(service_evidence.service_id(doc),'managed_service')

    def test_managed_engineering_does_not_select_only_survey(self):
        q='Kỹ thuật triển khai Managed Service cần làm gì và nghiệm thu thế nào?'
        found,route=rag.retrieve(q,self.documents,6)
        self.assertEqual(len(found),6)
        self.assertTrue(all(d['service_id']=='managed_service' for d in found))
        self.assertIn('service_sow',{d.get('data_type') for d in found})
        packing={};_,kept,size=rag.pack(q,found,18000,diagnostics=packing)
        present=packing['coverage']['services'][0]['present']
        for facet in ('tasks','acceptance','risks','survey'):self.assertIn(facet,present)
        self.assertLessEqual(size,18000)
        self.assertEqual(packing['coverage']['verification'],'evidence_types_only_not_entailment')

    def test_bom_and_effort_sources_retained(self):
        for q,id in [('BOM FortiGate','ND-1698D6BCA6EDA36A462E'),
                     ('SOW chuyển đổi cấu hình FortiGate và tổng giờ công','ND-94154164F98B2E2E4FCA')]:
            with self.subTest(question=q):
                found,_=rag.retrieve(q,self.documents,6)
                _,kept,_=rag.pack(q,found,rag.budgets(q,18000,2400)[0])
                self.assertIn(id,{d['id'] for d in kept})

    def test_allowed_documents_only_and_no_cross_service_fill(self):
        allowed=[d for d in self.documents if service_evidence.service_id(d)=='managed_service']
        found,_=rag.retrieve('SOW BOM Managed Service',allowed,6)
        self.assertTrue({d['id'] for d in found}<={d['id'] for d in allowed})
        self.assertNotIn('bom',set().union(*(service_evidence.facets(d) for d in found)))
        _,route=rag.retrieve('SOW BOM Managed Service',[],6)
        self.assertEqual(route['candidates'],0)
        unavailable,_=rag.retrieve('SOW BOM FortiGate',allowed,6)
        self.assertEqual(unavailable,[])

    def test_multi_service_preserves_links_and_available_coverage(self):
        found,route=rag.retrieve('SOW RMA và Managed Service',self.documents,6)
        self.assertEqual({d['service_id'] for d in found},{'rma','managed_service'})
        self.assertIn('corpus_coverage',route)

    def test_packing_reports_gaps_to_model_without_inventing_bom(self):
        q='SOW BOM Managed Service';found,_=rag.retrieve(q,self.documents,6)
        diagnostics={};messages,_,_=rag.pack(q,found,18000,diagnostics=diagnostics)
        self.assertIn('bom',diagnostics['coverage']['services'][0]['missing'])
        self.assertIn('không chứng minh toàn kho thiếu',messages[-1]['content'])
        summary=next(d for d in self.documents if d['id']=='ND-94154164F98B2E2E4FCA')
        linked=service_evidence.link(summary)
        self.assertEqual(linked['evidence_origin'],'calculated')
        self.assertEqual(linked['source_location']['source_cell'],'F28')

    def test_atomic_pack_omissions_and_distinct_versions(self):
        def doc(id,body,version='1'):
            return dict(id=id,title=id,body=body,version=version,review_status='reference',chunk=1)
        items=[doc('BIG','x'*10000),doc('SMALL','test'),doc('COPY','test'),doc('V2','test','2')]
        diagnostics={};messages,kept,size=rag.pack('DNS là gì?',items,4000,diagnostics=diagnostics)
        self.assertEqual([d['id'] for d in kept],['SMALL','V2'])
        self.assertEqual([d['reason'] for d in diagnostics['omitted']],['budget','duplicate'])
        self.assertIn('test',messages[-1]['content']);self.assertLessEqual(size,4000)
        with self.assertRaises(ValueError):rag.pack('x'*10000,items,3000)

    def test_role_templates_and_no_approval_promotion(self):
        q='SOW BOM Managed Service'
        self.assertIn('ĐỐI TƯỢNG SALES',rag.system_prompt(q,'sales'))
        self.assertIn('ĐỐI TƯỢNG KỸ SƯ',rag.system_prompt(q,'engineering'))
        self.assertIn('ĐỐI TƯỢNG KỸ SƯ',rag.system_prompt('Kỹ sư lập '+q))
        self.assertEqual(rag.system_prompt('DNS là gì?','sales'),rag.SYSTEM)
        with self.assertRaises(ValueError):service_evidence.audience(q,'admin')
        draft={**self.documents[0],'review_status':'draft_engineer_review'}
        linked=service_evidence.link(draft)
        self.assertEqual(linked['review_status'],draft['review_status'])
        self.assertEqual(linked['body'],draft['body']);self.assertNotIn('service_id',draft)


if __name__=='__main__':unittest.main()