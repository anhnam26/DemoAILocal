let historyOffset=0,historyQuery='',loadedMessages=[],olderBefore=null,historySearchTimer;
function displayConversation(items){
  loadedMessages=items;$('#messages').innerHTML='';$('#welcome').classList.toggle('hidden',items.length>0);
  items.forEach(m=>{appendUser(m.question);appendAnswer(m)});
  const last=items.at(-1);if(last)renderSources(last.sources,last.citations_verified);else{$('#sources').innerHTML='';$('#source-count').textContent='0'}
}
async function openConversation(id,title='Cuộc trò chuyện'){
  if(busy){toast('Chờ câu trả lời hiện tại hoàn tất trước khi đổi cuộc trò chuyện.');return}
  const d=await api('/conversations/'+encodeURIComponent(id));currentConversation=id;
  displayConversation(d.messages);olderBefore=d.next_before;$('#older-messages').classList.toggle('hidden',!d.has_more);
  $('#conversation-title').textContent=title;switchView('chat');$('.chat-main').scrollTop=0;
}
async function resumeRecentConversation(){
  const d=await api('/conversations');const last=d.items[0];
  if(last)await openConversation(last.id,last.title);else{displayConversation([]);$('#conversation-title').textContent='Trao đổi & giải đáp';$('#older-messages').classList.add('hidden')}
}
async function startConversation(){
  if(busy){toast('Chờ câu trả lời hiện tại hoàn tất trước khi mở cuộc trò chuyện mới.');return}
  const d=await api('/conversations',{method:'POST'});currentConversation=d.id;displayConversation([]);olderBefore=null;
  $('#older-messages').classList.add('hidden');$('#conversation-title').textContent='Trao đổi & giải đáp';switchView('chat');$('#question').focus();
}
async function loadConversations(more=false){
  if(!more){historyOffset=0;historyQuery=$('#history-search').value.trim()}
  const d=await api('/conversations?offset='+historyOffset+'&q='+encodeURIComponent(historyQuery));
  const html=d.items.map(c=>`<button class="doc-card conversation-card" data-conversation="${esc(c.id)}" data-title="${esc(c.title)}"><small>${esc(new Date(c.updated).toLocaleString('vi-VN'))} · ${c.message_count} lượt hỏi</small><h3>${esc(c.title)}</h3><p>Xem lại &amp; hỏi tiếp ↗</p></button>`).join('');
  if(more)$('#conversation-list').insertAdjacentHTML('beforeend',html);else $('#conversation-list').innerHTML=html||'<p class="muted">Chưa có cuộc trò chuyện phù hợp. Bắt đầu một câu hỏi mới để lưu lịch sử.</p>';
  historyOffset=d.next_offset;$('#history-more').classList.toggle('hidden',!d.has_more);
}
$('#history-new').onclick=()=>startConversation().catch(e=>toast(e.message));
$('#refresh-history').onclick=()=>loadConversations().catch(e=>toast(e.message));
$('#history-more').onclick=()=>loadConversations(true).catch(e=>toast(e.message));
$('#history-search').oninput=()=>{clearTimeout(historySearchTimer);historySearchTimer=setTimeout(()=>loadConversations().catch(e=>toast(e.message)),250)};
$('#older-messages').onclick=async()=>{try{const d=await api('/conversations/'+currentConversation+'?before='+olderBefore);displayConversation([...d.messages,...loadedMessages]);olderBefore=d.next_before;$('#older-messages').classList.toggle('hidden',!d.has_more)}catch(e){toast(e.message)}};
document.addEventListener('click',e=>{const b=e.target.closest('[data-conversation]');if(b)openConversation(b.dataset.conversation,b.dataset.title).catch(e=>toast(e.message))});

let sidebarClosed=innerWidth<=600;
try{const saved=localStorage.getItem('cyberant-sidebar-closed');if(saved!==null)sidebarClosed=saved==='true'}catch{}
function setSidebar(closed){
  sidebarClosed=closed;$('#workspace').classList.toggle('sidebar-closed',closed);$('#sidebar').inert=closed;
  $('#sidebar').setAttribute('aria-hidden',String(closed));$('#sidebar-toggle').setAttribute('aria-expanded',String(!closed));
  $('#sidebar-toggle').title=closed?'Mở thanh bên':'Thu gọn thanh bên';$('#sidebar-toggle').setAttribute('aria-label',$('#sidebar-toggle').title);
  $('#sidebar-backdrop').classList.toggle('hidden',closed||innerWidth>600);
  try{localStorage.setItem('cyberant-sidebar-closed',String(closed))}catch{}
}
$('#sidebar-toggle').onclick=()=>setSidebar(!sidebarClosed);$('#sidebar-backdrop').onclick=()=>setSidebar(true);
window.addEventListener('resize',()=>setSidebar(sidebarClosed));
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!sidebarClosed){setSidebar(true);$('#sidebar-toggle').focus()}});
document.addEventListener('click',e=>{if(innerWidth<=600&&e.target.closest('#sidebar [data-view]'))setSidebar(true)});
setSidebar(sidebarClosed);
