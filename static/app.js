const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
$('#question').maxLength=20000;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let currentConversation=null;
let currentUser=null,documents=[],health={},busy=false;
const fileControls=document.createElement('div');fileControls.className='chat-files';
const chatFiles=document.createElement('input');chatFiles.type='file';chatFiles.multiple=true;chatFiles.accept='.txt,.md,.csv,.pdf,.docx,.xlsx,.pptx';chatFiles.setAttribute('aria-label','Đính kèm tài liệu');
chatFiles.hidden=true;chatFiles.tabIndex=-1;
const attachButton=document.createElement('button');attachButton.type='button';attachButton.id='attach-file';attachButton.textContent='+';attachButton.setAttribute('aria-label','Thêm tài liệu');attachButton.title='Thêm tài liệu · tối đa 10 MB/file';attachButton.onclick=()=>chatFiles.click();
const attachedList=document.createElement('div');attachedList.setAttribute('aria-live','polite');fileControls.append(attachedList);$('#chat-form').prepend(fileControls);
$('#chat-form .composer-bottom').prepend(attachButton,chatFiles);
const fileHelp=document.createElement('details');fileHelp.className='attachment-help';
const helpTitle=document.createElement('summary');helpTitle.textContent='Thông tin chia sẻ';
const helpText=document.createElement('small');helpText.textContent='File chỉ thuộc chat này, nội dung có thể gửi tới model AI. Link HTTPS trong tin nhắn được đọc khi gửi; chỉ dùng link công khai, không chứa token bí mật. Tra cứu web chỉ dùng chủ đề công khai và quota server.';fileHelp.append(helpTitle,helpText);$('.composer-caption').append(fileHelp);
$('#question').placeholder='Nhắn tin, dán liên kết hoặc thả tài liệu…';
function resizeComposer(){const field=$('#question');field.style.height='auto';field.style.height=Math.min(field.scrollHeight,180)+'px'}
$('#question').addEventListener('input',resizeComposer);
const dropOverlay=document.createElement('div');dropOverlay.className='file-drop-overlay hidden';dropOverlay.textContent='Thả tài liệu để đính kèm';$('#view-chat').append(dropOverlay);
let fileBusy=false,chatController=null;
let scopeConversation=null,attachmentFiles=[],excludedFileUnits=new Set();
function selectedFileUnits(){return attachmentFiles.flatMap(f=>Array.from({length:f.units},(_,i)=>f.id+'-'+(i+1))).filter(id=>!excludedFileUnits.has(id))}
async function previewFile(cv,file,offset=0){
  if(busy||fileBusy||conversationLoading||currentConversation!==cv)return;
  const data=await api('/conversations/'+cv+'/attachments/'+file.id+'/preview?offset='+offset);
  if(currentConversation!==cv)return;
  $('#modal-title').textContent='Preview: '+data.name;
  $('#modal-meta').textContent=`extract-${data.extraction_version} · ${data.total} phần · checkbox chọn phạm vi lượt tiếp theo (không lưu server)`;
  const panel=$('#modal-body');panel.replaceChildren();$('#modal-references').replaceChildren();
  const warnings=document.createElement('p');warnings.textContent=data.warnings.join(' ');panel.append(warnings);
  const all=document.createElement('button');all.type='button';all.textContent='Chọn toàn bộ file';
  all.onclick=()=>{for(let i=1;i<=file.units;i++)excludedFileUnits.delete(file.id+'-'+i);renderAttachments();previewFile(cv,file,offset).catch(e=>toast(e.message))};
  const none=document.createElement('button');none.type='button';none.textContent='Bỏ chọn toàn bộ file';
  none.onclick=()=>{for(let i=1;i<=file.units;i++)excludedFileUnits.add(file.id+'-'+i);renderAttachments();previewFile(cv,file,offset).catch(e=>toast(e.message))};panel.append(all,none);
  for(const unit of data.items){
    const section=document.createElement('section'),label=document.createElement('label'),box=document.createElement('input');box.type='checkbox';box.checked=!excludedFileUnits.has(unit.id);
    box.onchange=()=>{if(box.checked)excludedFileUnits.delete(unit.id);else excludedFileUnits.add(unit.id);renderAttachments()};
    label.append(box,document.createTextNode(unit.location+' · '+unit.id));const text=document.createElement('pre');text.textContent=unit.body;
    section.append(label,text);
    if(unit.structure){const details=document.createElement('details'),summary=document.createElement('summary'),metadata=document.createElement('pre');summary.textContent='Cấu trúc / kiểu / cảnh báo';metadata.textContent=JSON.stringify(unit.structure,null,2);details.append(summary,metadata);section.append(details)}
    panel.append(section);
  }
  for(const [label,position] of [['Trang trước',offset?Math.max(0,offset-20):null],['Trang tiếp',data.next_offset]]){
    const button=document.createElement('button');button.type='button';button.textContent=label;button.disabled=position===null;button.onclick=()=>previewFile(cv,file,position).catch(e=>toast(e.message));panel.append(button);
  }
  if(!$('#document-modal').open)$('#document-modal').showModal();
}
const stopChat=document.createElement('button');stopChat.type='button';stopChat.textContent='■';stopChat.title='Dừng trả lời';stopChat.setAttribute('aria-label','Dừng trả lời');stopChat.className='hidden';stopChat.id='stop-chat';$('#chat-form .composer-bottom').append(stopChat);
stopChat.onclick=()=>chatController?.abort();
async function refreshAttachments(){
  if(!currentConversation){attachmentFiles=[];excludedFileUnits.clear();scopeConversation=null;renderAttachments();return}
  const cv=currentConversation,result=await api('/conversations/'+cv+'/attachments');if(cv!==currentConversation)return;
  if(scopeConversation!==cv){scopeConversation=cv;excludedFileUnits.clear()}
  attachmentFiles=result.items;
  const valid=new Set(attachmentFiles.flatMap(f=>Array.from({length:f.units},(_,i)=>f.id+'-'+(i+1))));excludedFileUnits=new Set([...excludedFileUnits].filter(id=>valid.has(id)));
  renderAttachments();
}
function renderAttachments(){
  attachedList.replaceChildren();
  const cv=currentConversation;
  for(const file of attachmentFiles){
    const row=document.createElement('article'),text=document.createElement('span'),remove=document.createElement('button');row.className='attachment-card';
    const name=document.createElement('b'),status=document.createElement('small');name.textContent=file.name;name.title=file.name;
    const selected=Array.from({length:file.units},(_,i)=>file.id+'-'+(i+1)).filter(id=>!excludedFileUnits.has(id)).length;
    status.textContent=`${selected}/${file.units} phần được chọn${file.warnings.length?' · Có lưu ý':''}`;text.append(name,status);
    const icon=document.createElement('span');icon.className='attachment-icon';icon.textContent='▤';icon.setAttribute('aria-hidden','true');
    remove.type='button';remove.textContent='Xóa file';remove.disabled=busy||fileBusy;
    remove.onclick=async()=>{if(busy||fileBusy||conversationLoading)return;if(!confirm('Xóa file khỏi hội thoại? Câu trả lời đã dùng file có thể bị thu hồi nguồn.'))return;fileBusy=true;updateChatControls();try{await api('/conversations/'+cv+'/attachments/'+file.id,{method:'DELETE'});await refreshAttachments()}catch(e){toast(e.message)}finally{fileBusy=false;updateChatControls()}};
    const preview=document.createElement('button');preview.type='button';preview.textContent='Preview / chọn phạm vi';preview.disabled=busy||fileBusy;
    preview.onclick=()=>previewFile(cv,file).catch(e=>toast(e.message));
    const menu=document.createElement('details'),summary=document.createElement('summary');menu.className='attachment-menu';summary.textContent='⋯';summary.setAttribute('aria-label','Thao tác '+file.name);summary.title='Thao tác tài liệu';menu.append(summary,preview,remove);
    row.append(icon,text,menu);attachedList.append(row);
  }
}
async function uploadChatFiles(files){
  if(busy||fileBusy||conversationLoading||!files.length)return;
  if(!currentConversation){const draft=$('#question').value;await startConversation();$('#question').value=draft;resizeComposer();if(!currentConversation)return}
  fileBusy=true;updateChatControls();
  let failed=false;
  try{
    for(const file of files){
      const progress=document.createElement('article');progress.className='attachment-card upload-status';progress.textContent=file.name+' · Đang tải và đọc…';attachedList.append(progress);
      try{
        if(file.size>10000000)throw Error('File vượt 10 MB.');
        if(!/\.(txt|md|csv|pdf|docx|xlsx|pptx)$/i.test(file.name))throw Error('Định dạng chưa hỗ trợ; nhận TXT/MD/CSV/PDF/DOCX/XLSX/PPTX.');
        const form=new FormData();form.append('file',file);
        await api('/conversations/'+currentConversation+'/attachments',{method:'POST',body:form});
        progress.textContent=file.name+' · Sẵn sàng';
      }catch(e){failed=true;progress.classList.add('upload-error');progress.textContent=file.name+' · '+e.message}
    }
    const errors=[...attachedList.querySelectorAll('.upload-error')];await refreshAttachments();attachedList.append(...errors);
    if(failed)toast('Một số file chưa được đọc. File thành công vẫn được giữ; không tự tải lại.');
  }catch(e){toast(e.message)}finally{fileBusy=false;chatFiles.value='';updateChatControls()}
}
chatFiles.onchange=()=>uploadChatFiles([...chatFiles.files]).catch(e=>toast(e.message));
let dragDepth=0;
const isFileDrag=e=>[...(e.dataTransfer?.types||[])].includes('Files');
const clearDrop=()=>{dragDepth=0;dropOverlay.classList.add('hidden')};
document.addEventListener('dragover',e=>{if(isFileDrag(e))e.preventDefault()});
document.addEventListener('drop',e=>{if(isFileDrag(e))e.preventDefault();clearDrop()});
$('#view-chat').addEventListener('dragenter',e=>{if(isFileDrag(e)){e.preventDefault();dragDepth++;if(!busy&&!fileBusy&&!conversationLoading)dropOverlay.classList.remove('hidden')}});
$('#view-chat').addEventListener('dragleave',e=>{if(isFileDrag(e)&&--dragDepth<=0)clearDrop()});
$('#view-chat').addEventListener('drop',e=>{if(!isFileDrag(e))return;e.preventDefault();clearDrop();uploadChatFiles([...e.dataTransfer.files]).catch(err=>toast(err.message))});
window.addEventListener('blur',clearDrop);
async function api(path,options={}){
  if(path==='/chat'&&typeof options.body==='string'){
    const body=JSON.parse(options.body);body.audience='auto';
    if(scopeConversation===currentConversation&&excludedFileUnits.size)body.file_unit_ids=selectedFileUnits();
    options={...options,body:JSON.stringify(body)};
    return streamChat(options);
  }
  let r;try{r=await fetch('/api'+path,{...options,headers:options.body instanceof FormData?{}:{'Content-Type':'application/json',...options.headers}})}
  catch{throw Error('Mất kết nối máy chủ. Kiểm tra mạng; yêu cầu có thể đã được xử lý. Hệ thống không tự gửi lại.')}
  if(r.status===401&&currentUser){currentUser=null;location.reload();throw Error('Phiên đăng nhập đã hết hạn.')}
  let d;try{d=await r.json()}catch{
    const errors={400:'Địa chỉ truy cập chưa hợp lệ. Kiểm tra APP_ORIGINS trên server.',403:'Yêu cầu bị chặn. Kiểm tra địa chỉ truy cập và APP_ORIGINS.',413:'Tệp hoặc yêu cầu vượt dung lượng cho phép.',502:'Máy chủ chưa sẵn sàng.',503:'Máy chủ tạm thời không khả dụng.',504:'Máy chủ phản hồi quá lâu. Kiểm tra lịch sử trước khi gửi lại.'};
    throw Error(errors[r.status]||'Không đọc được phản hồi máy chủ (HTTP '+r.status+').')
  }
  if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'Dữ liệu chưa hợp lệ (HTTP '+r.status+').');return d
}
async function streamChat(options){
  chatController=new AbortController();stopChat.classList.remove('hidden');$('#send').classList.add('hidden');
  try{
    const response=await fetch('/api/chat/stream',{...options,signal:chatController.signal,headers:{'Content-Type':'application/json'}});
    if(!response.ok){const data=await response.json().catch(()=>({}));throw Error(typeof data.detail==='string'?data.detail:'Không thể bắt đầu trả lời (HTTP '+response.status+').')}
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
    while(true){
      const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});
      let end;
      while((end=buffer.indexOf('\n\n'))>=0){
        const block=buffer.slice(0,end);buffer=buffer.slice(end+2);
        const line=block.split('\n').find(s=>s.startsWith('data: '));if(!line)continue;
        const event=JSON.parse(line.slice(6));
        if(event.type==='progress'){const indicator=$('#messages .thinking');if(indicator)indicator.textContent=event.stage+'…'}
        if(event.type==='error')throw Error(event.detail);
        if(event.type==='result')return event.data;
      }
    }
    throw Error('Kết nối kết thúc trước khi nhận kết quả. Kiểm tra lịch sử và usage; không tự gửi lại.');
  }catch(e){
    if(e.name==='AbortError')throw Error('Đã dừng chờ/xử lý. Provider có thể đã tính phí; kiểm tra lịch sử và usage trước khi gửi lại.');
    throw e;
  }finally{chatController=null;stopChat.classList.add('hidden');$('#send').classList.remove('hidden')}
}
async function copyAnswer(message){
  const text=message.dataset.answer;
  if(navigator.clipboard&&window.isSecureContext){try{await navigator.clipboard.writeText(text);toast('Đã sao chép câu trả lời.');return}catch{}}
  const field=document.createElement('textarea');field.value=text;field.className='clipboard-helper';field.setAttribute('aria-label','Nội dung sao chép');document.body.append(field);
  const previous=document.activeElement;let copied=false;
  try{field.focus();field.select();copied=document.execCommand('copy')}catch{}finally{field.remove();previous?.focus()}
  if(copied){toast('Đã sao chép câu trả lời.');return}
  const body=message.querySelector('.message-text');body.classList.remove('hidden');
  const range=document.createRange();range.selectNodeContents(body);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);
  toast('Trình duyệt chặn sao chép tự động. Nội dung đã được chọn; nhấn Ctrl+C hoặc dùng menu Sao chép.');
}
function toast(s){$('#toast').textContent=s;$('#toast').classList.remove('hidden');setTimeout(()=>$('#toast').classList.add('hidden'),5000)}
let modelSaving=false,modelVersion=0;
function updateChatControls(){
  attachButton.disabled=busy||fileBusy||conversationLoading;
  chatFiles.disabled=busy||fileBusy||conversationLoading;
  attachedList.querySelectorAll('button').forEach(b=>b.disabled=busy||fileBusy||conversationLoading);
  $('#chat-model').disabled=busy||modelSaving||conversationLoading||!health.allowed_models?.length;
  $('#send').disabled=busy||fileBusy||modelSaving||conversationLoading||!health.configured||!$('#chat-model').value;
  $('#new-chat').disabled=busy||fileBusy||conversationLoading;
  $('#question').disabled=conversationLoading;
  $('#older-messages').disabled=busy||conversationLoading;
}
function renderModel(data){
  health=data;const select=$('#chat-model'),valid=data.allowed_models.includes(data.model);
  select.innerHTML=(valid?'':'<option value="">Chọn model được cấp…</option>')+data.allowed_models.map(m=>`<option value="${esc(m)}">${esc(data.catalog?.find(item=>item.id===m)?.label||m)}</option>`).join('');
  select.value=valid?data.model:'';select.title=select.value;
  currentUser.model=data.model;currentUser.allowed_models=data.allowed_models;
  $('#model-pill').classList.toggle('off',!data.configured);
  $('#model-pill').textContent=data.configured?'Sẵn sàng':'Chưa sẵn sàng';
  $('#model-status').textContent=!data.allowed_models.length?'Chưa có model khả dụng. Liên hệ quản trị để được cấp model.':!valid?'Model đã chọn không còn được phép. Hãy chọn lại model.':!data.configured?'Chưa cấu hình kết nối AI. Liên hệ quản trị.':'Model áp dụng cho câu hỏi tiếp theo · Hạn mức dùng chung theo tài khoản';
  $('#model-status').classList.toggle('model-warning',!data.configured);updateChatControls();
  $('#model-status').classList.toggle('hidden',data.configured&&valid);
}
async function checkHealth(){try{if(!currentUser){await api('/health');return}const version=modelVersion,data=await api('/model');if(version===modelVersion&&!modelSaving)renderModel(data);await refreshAccountUsage()}catch{health.configured=false;updateChatControls();$('#model-pill').textContent='Mất kết nối hoặc hết phiên'}}
$('#chat-model').onchange=async()=>{
  const model=$('#chat-model').value;if(!model||busy||modelSaving)return;
  modelSaving=true;modelVersion++;updateChatControls();
  try{renderModel(await api('/model',{method:'PUT',body:JSON.stringify({model})}));toast('Đã chọn model cho các câu hỏi tiếp theo.');await refreshAccountUsage()}
  catch(e){health.configured=false;$('#chat-model').value='';toast(e.message)}finally{modelSaving=false;updateChatControls();await checkHealth()}
};
async function refreshAccountUsage(){if(!currentUser)return;const u=await api('/account/usage');$('#account-usage').textContent=`Tháng ${u.month} (UTC): ${u.used_tokens.toLocaleString('vi-VN')} / ${u.monthly_token_limit.toLocaleString('vi-VN')} token · Còn ${u.remaining_tokens.toLocaleString('vi-VN')} · Model ${u.model}`;}
const suggestions=[['QUY TRÌNH','RMA là gì và các bước thực hiện ra sao?'],['CẤU HÌNH','Cấu hình DHCP Server và Relay cần chuẩn bị gì?'],['KHẢO SÁT','Cần thu thập gì cho dịch vụ Managed Service?'],['AN TOÀN THÔNG TIN','Checklist ứng cứu khi nghi nhiễm ransomware gồm những gì?']];
async function enter(user){currentUser=user;$('#doc-search').value='';$('#doc-category').value='';$('#user-name').textContent=user.name;$('#user-role').textContent=user.role==='admin'?'Quản trị':'Thành viên';$('#admin-navigation').classList.toggle('hidden',user.role!=='admin');$('#account-nav').classList.toggle('hidden',user.role!=='admin');$('#user-avatar').textContent=user.role==='admin'?'QT':'TV';$('#admin-nav').classList.toggle('hidden',user.role!=='admin');$('#users-nav').classList.toggle('hidden',user.role!=='admin');$('#system-nav').classList.toggle('hidden',user.role!=='admin');$('#feedback-nav').classList.toggle('hidden',user.role!=='admin');$('#account-description').textContent=user.name+' · '+user.username+' · '+user.title;$('#messages').innerHTML='';$('#welcome').classList.remove('hidden');$('#suggestions').innerHTML=suggestions.map(([topic,q])=>`<button class="suggestion" data-question="${esc(q)}"><span class="topic">${esc(topic)}</span><b>${esc(q)}</b><span class="arrow">↗</span></button>`).join('');await loadDocuments();switchView('chat');await checkHealth();currentConversation=null;try{await resumeRecentConversation()}catch(e){toast(e.message)}$('#login').classList.add('hidden');$('#workspace').classList.remove('hidden');$('.chat-main').scrollTop=loadedMessages.length?$('.chat-main').scrollHeight:0}
async function loadDocuments(){documents=await api('/documents');$('#doc-count').textContent=documents.length;const category=$('#doc-category').value;$('#doc-category').innerHTML='<option value="">Tất cả chủ đề</option>'+[...new Set(documents.map(d=>d.category))].sort().map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');$('#doc-category').value=category;renderDocuments()}
function renderDocuments(){const q=$('#doc-search').value.toLocaleLowerCase('vi');const category=$('#doc-category').value;const list=documents.filter(d=>(!category||d.category===category)&&(d.title+' '+d.id+' '+d.category).toLocaleLowerCase('vi').includes(q));$('#knowledge-count').textContent=list.length+' tài liệu dùng chung';$('#doc-grid').innerHTML=list.map(d=>`<button class="doc-card" data-doc="${esc(d.id)}"><small>${esc(d.category.toUpperCase())} / ${esc(d.id)}</small><h3>${esc(d.title)}</h3><p>Nhóm ${esc(d.group)} · ${d.review_status==='accepted'?'Đã chấp nhận sử dụng':d.review_status==='draft_engineer_review'?'Bản nháp cần kỹ sư rà soát':'Tài liệu tham khảo'}</p></button>`).join('')||'<p class="muted">Không có tài liệu phù hợp bộ lọc.</p>'}
const titles={feedback:'Phản hồi chất lượng',chat:'Trợ lý AI',knowledge:'Kho tri thức',history:'Lịch sử trò chuyện',system:'Hệ thống',admin:'Quản trị tri thức',users:'Người dùng',account:'Tài khoản'};
function switchView(view){if(['admin','users','system','feedback','account'].includes(view)&&currentUser?.role!=='admin')return;$$('main>.view').forEach(v=>v.classList.toggle('hidden',v.id!=='view-'+view));$$('nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));$('#view-title').textContent=titles[view];if(view==='feedback')loadFeedback().catch(e=>toast(e.message));if(view==='admin')loadAdmin().catch(e=>toast(e.message));if(view==='system'){checkHealth();loadSystem().catch(e=>toast(e.message))}if(view==='account')refreshAccountUsage().catch(e=>toast(e.message));if(view==='users')loadUsers().catch(e=>toast(e.message));}
function appendUser(text){const div=document.createElement('div');div.className='message user';div.textContent=text;$('#messages').append(div)}
function appendAnswer(data){
  const div=document.createElement('div');div.dataset.answer=data.answer;div.className='message assistant';
  div.innerHTML=`<div class="message-label">✧ TRẢ LỜI ${$$('.message.assistant').length+1} ${data.needs_review?'<span class="review-tag">Cần xác minh / duyệt</span>':''}</div><div class="answer-toolbar"><button data-copy-answer title="Sao chép nội dung">Sao chép</button><button data-save-answer title="Lưu thành file Markdown">Lưu .md</button><button data-collapse-answer aria-expanded="true">Thu gọn</button></div><div class="message-text">${renderAnswer(data.answer)}</div><div class="message-footer"><span>${esc(data.model||'')} · ${esc(data.mode)} · ${esc(data.elapsed)}s${data.usage?.prompt_tokens!==undefined?' · '+esc(data.usage.prompt_tokens)+' token vào / '+esc(data.usage.completion_tokens)+' token ra':''}${data.usage?.cost!==undefined?' · $'+esc(data.usage.cost):''}</span>${(data.sources||[]).map(s=>`<button data-doc="${esc(s.id)}">▤ ${esc(s.id)}</button>`).join('')}<button data-feedback="1" data-chat="${data.chat_id}" title="Hữu ích">＋ Hữu ích</button><button data-feedback="-1" data-chat="${data.chat_id}" title="Cần sửa">Báo sai</button></div>`;
  for(const source of data.web_sources||[]){
    try{
      const url=new URL(source.url);if(url.protocol!=='https:'||url.username||url.password)continue;
      const link=document.createElement('a');link.className='web-source';link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';
      link.textContent=`🌐 ${source.id} · ${source.title}`;link.title=`${url.hostname} · Tra cứu ${source.retrieved_at||''}`;
      div.querySelector('.message-footer').append(link);
    }catch{}
  }
  $('#messages').append(div);
  if(data.truncated){
    const next=document.createElement('button');next.type='button';next.textContent='Tiếp tục câu trả lời';
    next.onclick=()=>{if(!busy&&!fileBusy)ask('Tiếp tục hướng dẫn ở trên')};div.querySelector('.answer-toolbar').append(next);
  }
  if(data.evidence_items?.length){
    const section=document.createElement('section');section.className='message-text source-appendix';
    const heading=document.createElement('h3');heading.textContent=`Dữ liệu nguồn đầy đủ: ${data.evidence_items.length} bản ghi`;section.append(heading);
    const note=document.createElement('p');note.textContent='Nội dung nguồn bên dưới được hiển thị nguyên vẹn, độc lập với phần tổng hợp AI. Không tự trở thành báo giá hoặc cam kết; giữ riêng từng phiên bản/phạm vi.';section.append(note);
    const table=document.createElement('table'),header=document.createElement('tr');
    for(const label of ['Dịch vụ','Bản ghi nguồn','Phiên bản','Nguồn gốc']){const th=document.createElement('th');th.textContent=label;header.append(th)}
    const thead=document.createElement('thead');thead.append(header);table.append(thead);
    const tbody=document.createElement('tbody');
    for(const item of data.evidence_items){const row=document.createElement('tr');for(const value of [item.service_id,`${item.title} [${item.id}]`,item.version,Object.values(item.source_location||{}).join(' · ')]){const cell=document.createElement('td');cell.textContent=value;row.append(cell)}tbody.append(row)}
    table.append(tbody);const scroll=document.createElement('div');scroll.className='table-scroll';scroll.append(table);section.append(scroll);
    for(const item of data.evidence_items){
      const title=document.createElement('h4');title.textContent=`${item.service_id} · ${item.title} [${item.id}] · ${item.version} · ${item.review_status||''}`;
      const location=document.createElement('small');location.textContent=Object.entries(item.source_location||{}).map(([k,v])=>`${k}: ${v}`).join(' · ');
      const body=document.createElement('pre');body.className='source-record';body.textContent=item.body;
      section.append(title,location,body);
    }
    div.append(section);
  }
}
async function ask(q){if(busy||fileBusy||modelSaving||conversationLoading)return;const model=$('#chat-model').value;if(!model||!health.configured){toast($('#model-status').textContent);return}busy=true;updateChatControls();$('#welcome').classList.add('hidden');appendUser(q);$('#question').value='';resizeComposer();$('#send').disabled=true;const indicator=document.createElement('div');indicator.className='thinking';indicator.textContent='Đang kiểm tra nguồn…';$('#messages').append(indicator);$('.chat-main').scrollTop=$('.chat-main').scrollHeight;try{const data=await api('/chat',{method:'POST',body:JSON.stringify({question:q,conversation_id:currentConversation,model})});currentConversation=data.conversation_id;indicator.remove();appendAnswer(data);loadedMessages.push({...data,question:q});if(['Trao đổi & giải đáp','Cuộc trò chuyện mới'].includes($('#conversation-title').textContent))$('#conversation-title').textContent=q.slice(0,100);refreshAccountUsage().catch(()=>{})}catch(e){indicator.className='message assistant';indicator.textContent=e.message;toast(e.message)}finally{busy=false;updateChatControls();checkHealth();loadConversations().catch(e=>toast(e.message));const last=$$('.message.assistant').at(-1),panel=$('.chat-main');if(last){if(innerWidth<=600)last.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});else panel.scrollTop+=last.getBoundingClientRect().top-panel.getBoundingClientRect().top-20}}}
function showDoc(d){$('#modal-title').textContent=d.title;$('#modal-meta').textContent=`${d.id} · ${d.version} · ${d.owner} · ${d.status} · ${d.review_status||'reference'}`;$('#modal-body').innerHTML=renderAnswer(d.body);$('#modal-references').innerHTML=(d.references||[]).filter(r=>{try{return new URL(r.url).protocol==='https:'}catch{return false}}).map(r=>`<p><a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">${esc(r.title)} ↗</a><br><small>Kiểm nguồn: ${esc(r.checked_at)}</small></p>`).join('');$('#document-modal').showModal()}
async function loadAdmin(){const data=await api('/admin');window.adminDocs=data.documents;$('#admin-docs').innerHTML=data.documents.map(d=>`<div class="admin-row"><b>${esc(d.title)}</b><small>${esc(d.status)} · ${esc(d.roles.join(', '))}</small><button data-preview="${esc(d.id)}">Đọc</button>${d.status!=='approved'?`<button data-action="approve" data-id="${esc(d.id)}">Duyệt</button>`:`<button data-action="retire" data-id="${esc(d.id)}">Thu hồi</button>`}</div>`).join('');$('#audit-log').innerHTML=data.audit.map(r=>`<div><time>${esc(new Date(r.ts).toLocaleString('vi-VN'))}</time><b>${esc(r.action)}</b><span>${esc(r.role)} · ${esc(r.detail)}</span></div>`).join('')}
document.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;try{if(b.hasAttribute('data-copy-answer')){await copyAnswer(b.closest('.message'))}if(b.hasAttribute('data-save-answer')){const blob=new Blob([b.closest('.message').dataset.answer],{type:'text/markdown;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='CyberAnt-tra-loi-'+Date.now()+'.md';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}if(b.hasAttribute('data-collapse-answer')){const body=b.closest('.message').querySelector('.message-text'),closed=body.classList.toggle('hidden');b.setAttribute('aria-expanded',String(!closed));b.textContent=closed?'Mở câu trả lời':'Thu gọn'}if(b.dataset.view)switchView(b.dataset.view);if(b.dataset.question){switchView('chat');ask(b.dataset.question)};if(b.dataset.doc)showDoc(await api('/documents/'+encodeURIComponent(b.dataset.doc)));if(b.dataset.feedback){openFeedback(Number(b.dataset.chat),Number(b.dataset.feedback))}if(b.dataset.preview)showDoc(window.adminDocs.find(d=>d.id===b.dataset.preview));if(b.dataset.action){await api(`/admin/documents/${encodeURIComponent(b.dataset.id)}/${b.dataset.action}`,{method:'POST'});await loadAdmin();await loadDocuments();toast('Đã cập nhật trạng thái tài liệu')}}catch(err){toast(err.message)}});
$('#logout').onclick=async()=>{try{await api('/logout',{method:'POST'});location.reload()}catch(e){toast(e.message)}};
$('#chat-form').onsubmit=e=>{e.preventDefault();if(fileBusy)return;const q=$('#question').value.trim();if(q.length>=2)ask(q)};
$('#question').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing&&e.keyCode!==229){e.preventDefault();$('#chat-form').requestSubmit()}};
$('#doc-search').oninput=renderDocuments;$('#doc-category').onchange=renderDocuments;$('#close-modal').onclick=()=>$('#document-modal').close();$('#refresh-health').onclick=()=>{checkHealth();loadSystem(true).catch(e=>toast(e.message))};
$('#upload-form').onsubmit=async e=>{e.preventDefault();const f=new FormData();f.append('file',$('#upload-file').files[0]);f.append('audience',$('#audience').value);try{await api('/admin/upload',{method:'POST',body:f});await loadAdmin();$('#upload-form').reset();toast('Tài liệu đang chờ duyệt; chưa được dùng để trả lời.')}catch(err){toast(err.message)}};
(async()=>{try{const u=await api('/me');await enter(u)}catch{}await checkHealth();setInterval(checkHealth,30000)})();

$('#new-chat').onclick=()=>startConversation().catch(e=>toast(e.message));

// Reading size is fixed by CSS; ignore preferences from earlier versions.
