"""Conservative service links and evidence-type coverage, not factual verification."""
import re
import unicodedata


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFD',text.lower().replace('đ','d'))
                   if unicodedata.category(c)!='Mn')


SERVICES={
    'managed_service':('managed service','managed_service','quan tri van hanh'),
    'configuration_migration':('chuyen doi cau hinh','configuration migration','configuration_migration','migration'),
    'fortigate_configuration':('cau hinh fortigate','fortigate_configuration'),
    'equipment_rental':('cho thue','rental service','equipment_rental'),
    'rma':('rma',),
    'remote_support':('ho tro tu xa','ho tro ky thuat','remote_support','technical support'),
    'consulting':('tu van cntt','khao sat tu van','khao sat/tu van','consulting'),
    'it_configuration':('dich vu cau hinh','dich vu trien khai cntt','it_configuration'),
}
FILE_SERVICES={
    'Managed Service.docx':'managed_service',
    'Rental service.docx':'equipment_rental',
    'RMA Service.docx':'rma',
    'dịch vụ cấu hình.docx':'it_configuration',
    'Dịch vụ triển khai CNTT.docx':'it_configuration',
    'Dịch vụ tư vấn CNTT.docx':'consulting',
}
WORKFLOW_SERVICES={
    'WF-01':'rma','WF-02':'rma','WF-03':'it_configuration','WF-04':'it_configuration',
    'WF-05':'configuration_migration','WF-06':'it_configuration',
    'WF-07':'equipment_rental','WF-08':'remote_support',
}
FACET_LABELS={
    'survey':'khảo sát/đầu vào','scope':'phạm vi/ngoài phạm vi','tasks':'công việc',
    'workflow':'luồng thực hiện','effort':'ước tính giờ công','bom':'quy tắc BOM',
    'acceptance':'nghiệm thu/bàn giao','risks':'rủi ro/rollback',
}


def contains(text,term):
    return bool(re.search(r'(?<![a-z0-9])'+re.escape(term)+r'(?![a-z0-9])',text))


def resolve_services(question):
    q=normalize(question)
    services=[key for key,terms in SERVICES.items() if any(contains(q,t) for t in terms)]
    # "FortiGate" inside a migration is the device, not a second configuration service.
    if 'configuration_migration' not in services and 'fortigate_configuration' not in services:
        if (contains(q,'fortigate') or (contains(q,'fortinet') and contains(q,'firewall'))) and re.search(r'\b(bom|sow|cau hinh)\b',q):
            services.append('fortigate_configuration')
    if 'configuration_migration' in services:
        services=[s for s in services if s!='fortigate_configuration']
    if 'fortigate_configuration' in services:
        services=[s for s in services if s!='it_configuration']
    return services


def service_id(doc):
    explicit=doc.get('service_id')
    if explicit in SERVICES:return explicit
    legacy=doc.get('service')
    if legacy in SERVICES:return legacy
    if legacy in FILE_SERVICES:return FILE_SERVICES[legacy]
    provenance=doc.get('provenance')
    provenance=provenance if isinstance(provenance,dict) else {}
    if doc.get('data_type')=='workflow':
        return WORKFLOW_SERVICES.get(provenance.get('workflow_id'))
    return FILE_SERVICES.get(provenance.get('file') or provenance.get('source_file'))


def facets(doc):
    """Type/section markers only; a marker does not certify completeness or entailment."""
    typ=doc.get('data_type');body=normalize(doc['body']);result=set()
    if typ=='service_requirements':result.add('survey')
    if typ=='workflow':result.add('workflow')
    if typ in ('service_sow','migration_sow'):result.add('tasks')
    if typ in ('migration_sow','migration_summary'):result.add('effort')
    if typ=='bom_rules':result.add('bom')
    if typ not in ('glossary','service_requirements','workflow'):
        if 'pham vi dich vu' in body or 'ngoai pham vi' in body:result.add('scope')
        if 'nghiem thu:' in body or 'ban giao:' in body:result.add('acceptance')
        if 'rollback:' in body or 'rui ro:' in body:result.add('risks')
    return result


def link(doc):
    provenance=doc.get('provenance')
    provenance=provenance if isinstance(provenance,dict) else {}
    origin=provenance.get('provenance')
    if origin=='source' or doc.get('review_status')=='source_transcribed':evidence='transcribed'
    elif origin=='derived_from_source':evidence='calculated'
    elif origin in ('source_estimate_with_authored_guidance','source_item_with_authored_guidance'):evidence='mixed_source_and_authored'
    elif origin=='authored_guidance':evidence='authored'
    else:evidence='reference_unverified'
    location={key:provenance[key] for key in ('source_file','source_sheet','source_row','source_cell','source_page') if key in provenance}
    if not location and provenance.get('file'):location['source_file']=provenance['file']
    return {**doc,'service_id':service_id(doc),'evidence_facets':sorted(facets(doc)),
            'evidence_origin':evidence,'source_location':location}


def requirements(question,kind):
    if not resolve_services(question):return []
    q=normalize(question)
    required=[]
    if kind=='survey':required=['survey','scope']
    elif kind in ('sow','sow_bom'):required=['tasks','acceptance','risks','scope','survey']
    elif kind=='bom':required=['bom','survey','scope']
    elif kind in ('procedure','troubleshooting'):required=['tasks','acceptance','risks','workflow','survey']
    if kind=='sow_bom':required.insert(0,'bom')
    if re.search(r'\b(gio cong|man.hour|uoc tinh|effort|thoi luong)\b',q):required.insert(0,'effort')
    return list(dict.fromkeys(required))


def coverage(question,kind,documents):
    required=requirements(question,kind);services=resolve_services(question);items=[]
    for service in services:
        available=set().union(*(facets(d) for d in documents if service_id(d)==service))
        present=[f for f in required if f in available]
        items.append(dict(service_id=service,required=required,present=present,
                          missing=[f for f in required if f not in available]))
    return dict(verification='evidence_types_only_not_entailment',services=items)


def audience(question,requested='auto'):
    if requested not in ('auto','sales','engineering'):raise ValueError('Đối tượng trả lời không hợp lệ')
    if requested!='auto':return requested
    q=normalize(question)
    if re.search(r'\b(ky su|ky thuat|engineer)\b',q):return 'engineering'
    if re.search(r'\b(sale|sales|kinh doanh)\b',q):return 'sales'
    return 'general'


def guidance(question,kind,requested='auto'):
    if kind not in ('sow','bom','sow_bom') and not requirements(question,kind):return ''
    role=audience(question,requested)
    common='''\nYÊU CẦU ĐẦU RA DỊCH VỤ: Chi tiết đủ dùng, không rút thành vài gạch đầu dòng chung chung.
Tách dữ kiện có nguồn, nội dung dự thảo và mục chưa xác nhận. Không biến bản nháp hoặc bài quảng bá thành cam kết.
Chỉ trình bày các phần được hỏi: SOW nêu đầu vào, phạm vi/ngoài phạm vi, công việc, trách nhiệm, deliverable, nghiệm thu và rủi ro/rollback có nguồn.
BOM tách thiết bị/license khỏi dòng dịch vụ/nhân công; nêu đơn vị, cơ sở số lượng, thời hạn và nguồn SKU. Thiếu thì ghi CHƯA XÁC NHẬN, không tự chọn SKU, giá, hãng, số lượng.
Dấu X/Mặc định không phải số lượng; mã nội bộ không phải SKU hãng. Man-hour không phải thời gian dự án hoặc downtime. Ước tính chỉ áp dụng khi các giả định/khóa dự án được xác nhận.
Nêu rõ thông tin cần bổ sung và tác động tới SOW/BOM. Nguồn mâu thuẫn: giữ khác biệt theo gói/phạm vi và yêu cầu xác nhận; không tự chọn một bên.
Trích [ID] sát nhận định/bảng; không coi có mã trích dẫn là chứng nhận đúng nội dung.'''
    if role=='sales':
        common+='\nĐỐI TƯỢNG SALES: Tóm tắt nhu cầu, câu hỏi khảo sát ưu tiên, SOW/BOM dự thảo theo yêu cầu, giả định và mục phải chuyển kỹ sư duyệt. Không trình bày dự thảo như báo giá/hợp đồng chính thức.'
    elif role=='engineering':
        common+='\nĐỐI TƯỢNG KỸ SƯ: Nêu baseline/điều kiện đầu vào, công việc theo giai đoạn và dependency, cách tính effort nếu có, kiểm thử pass/fail, bằng chứng nghiệm thu, điều kiện dừng và rollback có nguồn.'
    else:
        common+='\nĐỐI TƯỢNG CHUNG: Trình bày dự thảo nội bộ với phần khảo sát và phần triển khai tách rõ; không tự suy đoán vai trò hoặc hồ sơ khách hàng.'
    return common