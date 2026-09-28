from pathlib import Path
import re
p=Path('static/index.html');s=p.read_text(encoding='utf8')
s=s.replace('<script src="/static/finance.js" defer></script>','')
for view in ('operations','finance'):
    s=re.sub(r'<button data-view="'+view+r'".*?</button>','',s)
    s=re.sub(r'<section id="view-'+view+r'".*?</section>','',s,flags=re.S)
replacements={
'Không gian AI nội bộ dành cho đội ngũ kinh doanh và kỹ thuật. Chạy ngay trên GPU của bạn.':'Một kho tri thức chung cho cả đội ngũ. Tra cứu tài liệu, quy trình và hướng dẫn kỹ thuật.',
'Local inference · Qwen3.5-9B':'Local hoặc OpenRouter API',
'sales / kythuat / admin':'Tên tài khoản',
'Quản trị cấp tài khoản và quyền khách hàng. Ba vai trò: Sales, Kỹ thuật, Quản trị.':'Thành viên dùng chung kho tri thức; quản trị quản lý tài liệu và tài khoản.',
'Hệ thống local':'Hệ thống',
'Dữ liệu ở trên máy bạn':'Kho tri thức chung',
'Tra cứu nội bộ. Không sử dụng cloud LLM.':'Chế độ API gửi câu hỏi và các đoạn nguồn liên quan tới OpenRouter.',
'Hồ sơ công ty là DEMO. Tri thức chuyên ngành có nguồn tham khảo; giá, lịch và SLA thật cần phê duyệt.':'Tài liệu lý thuyết và hướng dẫn tham khảo. Bản nháp kỹ thuật, giá và SLA cần kiểm tra trước khi áp dụng.',
'✧ Qwen3.5-9B':'✧ Trợ lý tri thức',
'Kho chung cho Sales, Kỹ thuật và Quản trị.':'Kho chung cho mọi thành viên.',
'<option value="sale">Sales</option><option value="technical">Kỹ thuật</option>':'<option value="member">Thành viên</option>',
'<label>Khách được phân công (A,C,E…)<input id="user-customers" placeholder="A,C,E,G,I"></label>':'',
'Máy chủ &amp; model local':'Máy chủ &amp; model',
'<h2>Cấu hình model</h2>':'<h2>Cấu hình model local</h2>',
'Không có cloud fallback; chỉ điều khiển model thuộc thư mục này.':'Chọn local để xử lý trên máy hoặc OpenRouter để gọi API. Không tự chuyển nhà cung cấp khi lỗi.',
}
for a,b in replacements.items():s=s.replace(a,b)
s=s.replace('<div id="system-info"', '<div class="card"><h2>Chế độ trả lời</h2><form id="provider-form"><label>Model chạy bằng<select id="provider-mode"><option value="openrouter">OpenRouter API</option><option value="local">Local GPU</option></select></label><button class="primary">Áp dụng</button></form><p id="provider-summary"></p><button class="secondary" id="sync-knowledge">Đồng bộ kho tri thức</button></div><div id="system-info"')
p.write_text(s,encoding='utf8')
p=Path('static/app.js');s=p.read_text(encoding='utf8')
s=s.replace("health.ready?'Qwen3.5-9B · Local':'Model chưa sẵn sàng'","health.ready?esc(health.model)+' · '+(health.mode==='openrouter'?'API đã cấu hình':'Local'):'Model chưa sẵn sàng'")
s=s.replace("['MODEL','Qwen3.5-9B Q4_K_M'","['MODEL',health.model||'Chưa cấu hình'")
start=s.index('const suggestionsSale=');end=s.index('async function enter',start)
s=s[:start]+'''const suggestions=[['QUY TRÌNH','RMA là gì và các bước thực hiện ra sao?'],['CẤU HÌNH','Cấu hình DHCP Server và Relay cần chuẩn bị gì?'],['KHẢO SÁT','Cần thu thập gì cho dịch vụ Managed Service?'],['AN TOÀN THÔNG TIN','Checklist ứng cứu khi nghi nhiễm ransomware gồm những gì?']];
'''+s[end:]
s=s.replace("$('#operation-kind').value='';$('#operation-search').value='';",'')
s=s.replace("user.role==='sale'?'MA':user.role==='technical'?'HN':'QT'","user.role==='admin'?'QT':'TV'")
s=s.replace("(user.role==='sale'?suggestionsSale:suggestionsTech)","suggestions")
s=s.replace("system:'Hệ thống local'","system:'Hệ thống'")
s=s.replace("if(view==='finance')loadFinance().catch(e=>toast(e.message));if(view==='operations')loadOperations().catch(e=>toast(e.message))",'')
s=s.replace('Đang tra cứu / chờ lượt xử lý trên GPU.','Đang tra cứu tài liệu và tổng hợp câu trả lời.')
s=s.replace("${esc(data.elapsed)}s</span>","${esc(data.elapsed)}s${data.usage?.prompt_tokens!==undefined?' · '+esc(data.usage.prompt_tokens)+' token vào / '+esc(data.usage.completion_tokens)+' token ra':''}${data.usage?.cost!==undefined?' · $'+esc(data.usage.cost):''}</span>")
s=s.replace("${esc(d.version)} · Hiệu lực đến ${esc(d.valid_to)}","Nhóm ${esc(d.group)} · ${d.review_status==='draft_engineer_review'?'Bản nháp cần kỹ sư rà soát':'Tài liệu tham khảo'}")
s=s.replace("${d.status} · Đến ${d.valid_to}","${d.status} · ${d.review_status||'reference'}")
start=s.index('async function loadOperations()');end=s.index("$('#new-chat').onclick",start);s=s[:start]+s[end:]
p.write_text(s,encoding='utf8')
p=Path('static/management.js');s=p.read_text(encoding='utf8')
s=s.replace("{sale:'Sales',technical:'Kỹ thuật',admin:'Quản trị'}","{member:'Thành viên',admin:'Quản trị'}")
s=s.replace("'Vai trò / khách'","'Vai trò'").replace("+'<br>'+esc(u.customers.join(', '))",'')
s=s.replace("customers:$('#user-role-select').value==='admin'?[]:$('#user-customers').value.toUpperCase().split(',').map(x=>x.trim()).filter(Boolean)","customers:[]")
s=s.replace("$('#user-customers').value=u.customers.filter(x=>x!=='*').join(',');",'')
s=s.replace("try{const d=await api('/admin/system');", "try{const d=await api('/admin/system');$('#provider-mode').value=d.provider.mode;$('#provider-summary').textContent=d.provider.model+' · Ngân sách đầu vào '+d.provider.input_budget+' · Đầu ra '+d.provider.output_budget+' token';$('#runtime-form').classList.toggle('hidden',d.provider.mode!=='local');")
s=s.replace("b.disabled=d.generation_busy","b.disabled=d.generation_busy||d.provider.mode!=='local'")
s+='''
$('#provider-form').onsubmit=async e=>{e.preventDefault();try{await api('/admin/system/provider',{method:'PUT',body:JSON.stringify({mode:$('#provider-mode').value})});await checkHealth();await loadSystem(true);toast('Đã đổi chế độ trả lời.')}catch(err){toast(err.message)}};
$('#sync-knowledge').onclick=async()=>{const b=$('#sync-knowledge');b.disabled=true;try{const d=await api('/admin/knowledge/sync',{method:'POST'});await loadDocuments();toast('Đã đồng bộ '+d.documents+' tài liệu.')}catch(err){toast(err.message)}finally{b.disabled=false}};
'''
p.write_text(s,encoding='utf8')
