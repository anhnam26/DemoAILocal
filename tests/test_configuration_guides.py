"""Offline broad/narrow retrieval, unknown facts and bounded detailed guidance."""
import unittest
from cyberant import rag,service_evidence,sync_knowledge


class ConfigurationGuides(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.documents=sync_knowledge.load()

    def test_broad_and_narrow_recognition(self):
        for q in ('Cấu hình firewall Fortinet','Cấu hình FortiGate','Cấu hình firewall',
                  'Cấu hình switch Cisco','Cấu hình VLAN','Thiết lập VPN'):
            with self.subTest(q=q):
                self.assertTrue(rag.configuration(q)['broad'])
        for q in ('Cấu hình NAT FortiGate','Cấu hình Site-to-Site VPN FortiGate',
                  'Cấu hình DHCP Server','Cấu hình VLAN trunk Cisco'):
            with self.subTest(q=q):self.assertFalse(rag.configuration(q)['broad'])
        self.assertIsNone(rag.configuration('BOM FortiGate'))
        self.assertIsNone(rag.configuration('FortiGate là gì?'))
        self.assertEqual(service_evidence.resolve_services('Cấu hình firewall Fortinet'),['fortigate_configuration'])
        self.assertTrue(rag.is_followup('Tiếp tục hướng dẫn ở trên'))

    def test_fortinet_broad_sources_cover_required_topics(self):
        for q in ('Cấu hình firewall Fortinet','Cấu hình FortiGate','Cấu hình firewall'):
            with self.subTest(q=q):
                found,route=rag.retrieve(q,self.documents,24)
                self.assertFalse(route['configuration_coverage']['missing'])
                self.assertTrue(any(d.get('data_type')=='it_configuration' and 'nat' in rag.configuration_facets(d) for d in found))
                self.assertTrue(any(d.get('data_type')=='it_configuration' and 'policy' in rag.configuration_facets(d) for d in found))
                self.assertTrue(any(d['id'] in ('TECH-MOP','RUN-FIREWALL') for d in found))
                self.assertGreaterEqual(sum(d.get('data_type')=='it_configuration' for d in found),8)
                self.assertFalse(any('fortinac' in rag.norm(d['title']) for d in found))
                diag={};messages,packed,size=rag.pack(q,found,64000,diagnostics=diag)
                self.assertLessEqual(size,64000)
                self.assertFalse(diag['configuration_coverage']['missing'])
                self.assertIn('CÂU HỎI TỔNG THỂ',messages[0]['content'])
                self.assertNotIn('fortigate_configuration: luồng thực hiện',messages[-1]['content'])

    def test_narrow_sources_and_allowed_boundary(self):
        q='Cấu hình NAT FortiGate'
        found,_=rag.retrieve(q,self.documents,12)
        self.assertIn('ND-3514CCE3CD513F729662',{d['id'] for d in found[:3]})
        self.assertIn('CÂU HỎI TẬP TRUNG',rag.system_prompt(q))
        allowed=[d for d in self.documents if d['id']=='ND-3514CCE3CD513F729662']
        f,_=rag.retrieve(q,allowed,24)
        self.assertEqual({d['id'] for d in f},{allowed[0]['id']})
        f,_=rag.retrieve('Cấu hình firewall',[],24);self.assertEqual(f,[])

    def test_other_topics_and_unknown_fields(self):
        for q,topic in [('Cấu hình VLAN','vlan'),('Cấu hình switch Cisco','switch')]:
            found,route=rag.retrieve(q,self.documents,24)
            self.assertEqual(route['configuration_coverage']['topic'],topic)
            self.assertTrue(found)
            self.assertFalse(any('fortigate' in rag.norm(d['title']) for d in found))
        prompt=rag.system_prompt('Cấu hình firewall Fortinet')
        self.assertIn('không phải chứng nhận triển khai',prompt)
        self.assertIn('Không lấy ô trống làm lý do từ chối',prompt)
        self.assertIn('Không tạo lệnh cụ thể',prompt)


if __name__=='__main__':unittest.main()