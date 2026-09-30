let managedUsers=[],availableModels=[],systemLoading=false,usageOffset=0;
function selectedModels(){return $$('#user-models input:checked').map(input=>input.value)}
function updateModelCount(){const count=selectedModels().length;$('#user-model-count').textContent=count?'Đã chọn '+count+' model':'Chọn ít nhất một model';}
function renderModelChecks(selected=[]){
  const all=[...new Set([...availableModels,...selected])];
  $('#user-models').innerHTML=all.map(m=>`<label class="model-option"><input type="checkbox" value="${esc(m)}" ${selected.includes(m)?'checked':''}><span>${esc(m)}${availableModels.includes(m)?'':' <small class="form-error">Không còn cấu hình — bỏ chọn để lưu</small>'}</span></label>`).join('')||'<p class="form-error">Chưa cấu hình model trên máy chủ.</p>';
  updateModelCount();
}
$('#user-models').onchange=updateModelCount;
function hideLoginPassword(){const input=$('#login-password'),button=$('#toggle-login-password');input.type='password';button.textContent='Hiện';button.setAttribute('aria-label','Hiện mật khẩu');button.setAttribute('aria-pressed','false')}
$('#toggle-login-password').onclick=()=>{const input=$('#login-password'),button=$('#toggle-login-password'),show=input.type==='password';input.type=show?'text':'password';button.textContent=show?'Ẩn':'Hiện';button.setAttribute('aria-label',show?'Ẩn mật khẩu':'Hiện mật khẩu');button.setAttribute('aria-pressed',String(show))};
const roleLabel={member:'Thành viên',admin:'Quản trị'};
const fmt=n=>Number(n||0).toLocaleString('vi-VN');
const statusLabel={completed:'Đã ghi nhận',reserved:'Đang chờ',in_flight:'Đang gọi',uncertain:'Cần đối soát',cancelled:'Không gửi / bị từ chối'};
function dataTable(headers,rows){return '<div class="table-scroll"><table class="answer-table"><thead><tr>'+headers.map(x=>'<th>'+esc(x)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(x=>'<td>'+x+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>'}
$('#login-form').onsubmit=async e=>{e.preventDefault();$('#login-submit').disabled=true;$('#login-error').textContent='';try{const u=await api('/login',{method:'POST',body:JSON.stringify({username:$('#login-username').value.trim(),password:$('#login-password').value})});$('#login-password').value='';hideLoginPassword();await enter(u)}catch(err){$('#login-error').textContent=err.message}finally{$('#login-submit').disabled=false}};
$('#password-form').onsubmit=async e=>{e.preventDefault();try{await api('/account/password',{method:'POST',body:JSON.stringify({old_password:$('#old-password').value,new_password:$('#new-password').value})});location.reload()}catch(err){toast(err.message)}};
async function loadUsers(){
  const d=await api('/admin/users');managedUsers=d.users;
  $('#online-summary').textContent=d.online_count+' người online / '+d.users.length+' tài khoản';
  const selectedModelsBefore=selectedModels(),loaded=availableModels.length>0;availableModels=d.models;renderModelChecks(loaded?selectedModelsBefore:d.models.slice(0,1));
  $('#users-table').innerHTML=dataTable(['Tài khoản','Vai trò / model','Tháng '+d.month+' (UTC)','Trạng thái','Thao tác'],d.users.map(u=>[
    esc(u.name)+'<br><small>'+esc(u.username)+'</small>',esc(roleLabel[u.role])+'<div class="model-tags">'+u.allowed_models.map(m=>'<span>'+esc(m)+(d.models.includes(m)?'':' (không còn cấu hình)')+'</span>').join('')+'</div><small>Đang chọn: '+esc(u.model||'Chưa chọn')+'</small>',
    fmt(u.usage.used_tokens)+' / '+fmt(u.monthly_token_limit)+'<br><small>Đang giữ: '+fmt(u.usage.reserved_tokens)+' · Chưa rõ: '+fmt(u.usage.uncertain_tokens)+'<br>Còn: '+fmt(u.usage.remaining_tokens)+'</small>',
    esc(!u.active?'Đã khóa':u.online?'Online':'Offline'),`<button class="secondary" data-edit-user="${esc(u.id)}">Sửa / mật khẩu / hạn mức</button> <button class="secondary" data-reset-user="${esc(u.id)}">Cấp mật khẩu mới</button>`]));
  $('#sessions-table').innerHTML=dataTable(['Người dùng','Hoạt động cuối','Kết nối','Trạng thái','Thao tác'],d.sessions.map(s=>[esc(s.username),esc(new Date(s.last_seen*1000).toLocaleString('vi-VN')),esc(s.ip),s.online?'Online':'Không hoạt động',`<button class="secondary" data-revoke-session="${esc(s.sid)}">Đăng xuất phiên</button>`]));
  const selected=$('#usage-user').value;$('#usage-user').innerHTML='<option value="">Tất cả tài khoản</option>'+d.users.map(u=>`<option value="${esc(u.id)}">${esc(u.username)}</option>`).join('');$('#usage-user').value=selected;
  if(!$('#usage-month').value)$('#usage-month').value=d.month;
  await loadUsage();
}
function resetUserForm(){$('#user-form').reset();$('#edit-user-id').value='';$('#user-form-title').textContent='Tạo tài khoản';$('#user-active').checked=true;renderModelChecks(availableModels.slice(0,1))}
function showSecret(username,password){$('#new-user-secret').classList.remove('hidden');$('#new-user-secret').innerHTML='<b>'+esc(username)+'</b><p>Mật khẩu vừa cấp (chỉ hiển thị lần này):</p><code>'+esc(password)+'</code>'}
$('#cancel-user-edit').onclick=resetUserForm;$('#refresh-users').onclick=()=>loadUsers().catch(e=>toast(e.message));
$('#user-form').onsubmit=async e=>{e.preventDefault();if(!selectedModels().length){toast('Chọn ít nhất một model.');$('#user-models input')?.focus();return}const id=$('#edit-user-id').value;try{const d=await api('/admin/users'+(id?'/'+encodeURIComponent(id):''),{method:id?'PUT':'POST',body:JSON.stringify({username:$('#user-username').value.trim(),name:$('#user-fullname').value.trim(),role:$('#user-role-select').value,password:$('#user-password').value||null,active:$('#user-active').checked,allowed_models:selectedModels(),monthly_token_limit:Number($('#user-token-limit').value)})});if(d.temporary_password)showSecret(d.username,d.temporary_password);resetUserForm();toast('Đã lưu tài khoản.');await loadUsers()}catch(err){toast(err.message)}};
async function loadUsage(more=false){
  if(!more)usageOffset=0;
  const params=new URLSearchParams({month:$('#usage-month').value,offset:String(usageOffset)});if($('#usage-user').value)params.set('user_id',$('#usage-user').value);
  const d=await api('/admin/usage?'+params);
  $('#usage-summary').innerHTML=dataTable(['Tài khoản','Token vào','Token ra','Tổng đã dùng','Đang giữ','Chưa rõ','Chi phí đã biết (USD)'],d.users.map(u=>[esc(u.username),fmt(u.prompt_tokens),fmt(u.completion_tokens),fmt(u.used_tokens),fmt(u.reserved_tokens),fmt(u.uncertain_tokens),Number(u.cost).toFixed(6)]));
  const html=dataTable(['Thời gian','Tài khoản / model','Usage','Trạng thái','Đối soát'],d.records.map(r=>[esc(new Date(r.created*1000).toLocaleString('vi-VN')),esc(r.username)+'<br><small>'+esc(r.model)+'</small>',r.total_tokens===null?'Giữ '+fmt(r.reserved_tokens):fmt(r.prompt_tokens)+' vào + '+fmt(r.completion_tokens)+' ra = '+fmt(r.total_tokens),esc(statusLabel[r.status])+'<br><small>'+esc(r.note)+'</small>',r.status==='uncertain'?`<button data-reconcile="${esc(r.id)}">Đối soát</button><small>${esc(r.generation_id||'Không có mã generation')}</small>`:'—']));
  if(more)$('#usage-records').insertAdjacentHTML('beforeend',html);else $('#usage-records').innerHTML=html;
  usageOffset=d.next_offset;$('#usage-more').classList.toggle('hidden',!d.has_more);
}
$('#refresh-usage').onclick=()=>loadUsage().catch(e=>toast(e.message));$('#usage-more').onclick=()=>loadUsage(true).catch(e=>toast(e.message));
$('#reconcile-form').onsubmit=async e=>{e.preventDefault();try{await api('/admin/usage/'+$('#reconcile-id').value+'/reconcile',{method:'POST',body:JSON.stringify({prompt_tokens:Number($('#reconcile-prompt').value),completion_tokens:Number($('#reconcile-completion').value),note:$('#reconcile-note').value})});$('#reconcile-form').classList.add('hidden');await loadUsers();toast('Đã ghi nhận đối soát.')}catch(err){toast(err.message)}};
async function loadSystem(){
  if(systemLoading||currentUser?.role!=='admin')return;systemLoading=true;
  try{const d=await api('/admin/system');$('#metrics-time').textContent='Uptime '+Math.floor(d.uptime/60)+' phút · '+d.generation.active+' lượt đang chạy · '+d.generation.waiting+' đang chờ';
    $('#system-info').innerHTML=`<div class="card"><h3>OpenRouter API</h3><p>${d.provider.configured?'Đã cấu hình key/model':'Thiếu key hoặc model'}</p></div><div class="card"><h3>Ngân sách mỗi lượt</h3><p>Trần đầu vào ${fmt(d.provider.input_budget)} byte UTF-8 (không phải tokenizer) · Đầu ra tối đa ${fmt(d.provider.output_budget)} token; điều chỉnh theo câu hỏi</p></div>`;
    $('#provider-summary').innerHTML='<h2>Model cấu hình trong .env</h2>'+d.provider.models.map(m=>'<p>'+esc(m)+'</p>').join('')+'<p>Chọn model và hạn mức từng tài khoản trong mục Người dùng.</p>';
    $('#system-counts').innerHTML=Object.entries(d.database).map(([k,v])=>'<p>'+esc(k)+': '+fmt(v)+'</p>').join('');
  }finally{systemLoading=false}
}
$('#system-backup').onclick=async()=>{try{const d=await api('/admin/system/backup',{method:'POST'});toast('Đã sao lưu: '+d.path)}catch(e){toast(e.message)}};
$('#sync-knowledge').onclick=async()=>{const b=$('#sync-knowledge');b.disabled=true;try{const d=await api('/admin/knowledge/sync',{method:'POST'});await loadDocuments();toast('Đã đồng bộ '+d.documents+' tài liệu.')}catch(err){toast(err.message)}finally{b.disabled=false}};
document.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;try{
  if(b.dataset.editUser){$('#new-user-secret').textContent='';$('#new-user-secret').classList.add('hidden');const u=managedUsers.find(u=>u.id===b.dataset.editUser);$('#edit-user-id').value=u.id;$('#user-username').value=u.username;$('#user-fullname').value=u.name;$('#user-role-select').value=u.role;$('#user-active').checked=u.active;$('#user-password').value='';renderModelChecks(u.allowed_models);$('#user-token-limit').value=u.monthly_token_limit;$('#user-form-title').textContent='Sửa tài khoản';$('#user-form').scrollIntoView({block:'start'})}
  if(b.dataset.resetUser){const d=await api('/admin/users/'+b.dataset.resetUser+'/reset-password',{method:'POST'});showSecret(managedUsers.find(u=>u.id===b.dataset.resetUser)?.username,d.temporary_password);await loadUsers()}
  if(b.dataset.revokeSession){await api('/admin/sessions/'+b.dataset.revokeSession,{method:'DELETE'});await loadUsers();toast('Đã thu hồi phiên.')}
  if(b.dataset.reconcile){$('#reconcile-form').reset();$('#reconcile-id').value=b.dataset.reconcile;$('#reconcile-form').classList.remove('hidden');$('#reconcile-form').scrollIntoView({block:'start'})}
}catch(err){toast(err.message)}});
setInterval(async()=>{if(!currentUser)return;try{await api('/heartbeat',{method:'POST'})}catch{}},25000);
setInterval(()=>{if(currentUser?.role==='admin'&&!$('#view-system').classList.contains('hidden'))loadSystem().catch(()=>{})},15000);
$('#load-conversations').onclick=async()=>{try{const rows=await api('/admin/conversations');$('#admin-conversations').innerHTML=rows.map(r=>'<details class="card"><summary>'+esc(r.username)+' · '+esc(r.question)+'</summary><small>'+esc(r.ts)+'</small><div class="message-text">'+renderAnswer(r.answer)+'</div></details>').join('')}catch(e){toast(e.message)}};
