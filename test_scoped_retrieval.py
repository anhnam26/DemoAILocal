import re
import pytest
import rag,sync_knowledge

@pytest.mark.parametrize('question',['VLAN là gì?','Các bước cấu hình VLAN cơ bản','Cau hinh VLAN nhu the nao?'])
def test_generic_vlan_keeps_foundation_not_incidental_vendor(question):
    found,routing=rag.retrieve(question,sync_knowledge.load())
    _,selected,_=rag.pack(question,found,rag.budgets(question,18000,2400)[0])
    assert found[0]['id']=='KB-NET-VLAN'
    assert 'KB-NET-VLAN' in [d['id'] for d in selected]
    assert not any(re.search(r'fortinac|wi-fi',d['title'],re.I) for d in selected)
    assert rag.scope(question)=='generic'


def test_vendor_question_does_not_lose_vendor_source():
    docs=[sync_knowledge.document('GEN','VLAN','VLAN concept','A',scope='generic'),
          sync_knowledge.document('DEVICE','FortiNAC VLAN configuration','FortiNAC VLAN configuration details','B')]
    found,_=rag.retrieve('Cấu hình FortiNAC VLAN',docs)
    assert found[0]['id']=='DEVICE' and rag.scope('Cấu hình FortiNAC VLAN')=='device_specific'
