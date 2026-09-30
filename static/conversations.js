let historyOffset=0,historyQuery='',loadedMessages=[],olderBefore=null,historySearchTimer;
let historyItems=[],historyVersion=0,historyLoading=false,conversationLoading=false;
function displayConversation(items){
  loadedMessages=items;$('#messages').innerHTML='';$('#welcome').classList.toggle('hidden',items.length>0);
  items.forEach(m=>{appendUser(m.question);appendAnswer(m)});
}
function selectConversation(){
  $$('[data-conversation]').forEach(b=>{const active=b.dataset.conversation===currentConversation;b.setAttribute('aria-current',String(active));b.closest('.conversation-entry').classList.toggle('active',active)});
}
async function openConversation(id,title='Cuộc trò chuyện'){
  if(busy||conversationLoading){toast('Chờ thao tác hiện tại hoàn tất trước khi đổi cuộc trò chuyện.');return}
  conversationLoading=true;updateChatControls();
  try{
    const d=await api('/conversations/'+encodeURIComponent(id));currentConversation=id;
    displayConversation(d.messages);olderBefore=d.next_before;$('#older-messages').classList.toggle('hidden',!d.has_more);
    $('#question').value='';$('#conversation-title').textContent=title;switchView('chat');selectConversation();
    $('.chat-main').scrollTop=d.messages.length?$('.chat-main').scrollHeight:0;
    if(innerWidth<=600)setSidebar(true);
  }finally{conversationLoading=false;updateChatControls()}
}
async function resumeRecentConversation(){
  await loadConversations();const last=historyItems[0];
  if(last)await openConversation(last.id,last.title);else{displayConversation([]);$('#conversation-title').textContent='Cuộc trò chuyện mới';$('#older-messages').classList.add('hidden')}
}
async function startConversation(){
  if(busy||conversationLoading){toast('Chờ thao tác hiện tại hoàn tất trước khi mở cuộc trò chuyện mới.');return}
  conversationLoading=true;updateChatControls();
  try{
    const d=await api('/conversations',{method:'POST'});currentConversation=d.id;displayConversation([]);olderBefore=null;
    $('#question').value='';$('#older-messages').classList.add('hidden');$('#conversation-title').textContent='Cuộc trò chuyện mới';switchView('chat');
    $('#history-search').value='';clearTimeout(historySearchTimer);selectConversation();
    if(innerWidth<=600)setSidebar(true);
    await loadConversations();
  }finally{conversationLoading=false;updateChatControls();$('#question').focus({preventScroll:true});$('.chat-main').scrollTop=0}
}
function historyGroup(stamp){
  const date=new Date(stamp),today=new Date();today.setHours(0,0,0,0);
  const yesterday=new Date(today);yesterday.setDate(today.getDate()-1);
  const week=new Date(today);week.setDate(today.getDate()-7);
  if(date>=today)return 'Hôm nay';if(date>=yesterday)return 'Hôm qua';if(date>=week)return '7 ngày qua';
  return 'Tháng '+(date.getMonth()+1)+' / '+date.getFullYear();
}
function renderHistory(){
  let group='';
  $('#conversation-list').innerHTML=historyItems.map(c=>{
    const label=historyGroup(c.updated),heading=label!==group?`<h3 class="history-group">${esc(label)}</h3>`:'';group=label;
    return heading+`<article class="conversation-entry"><button class="conversation-card" data-conversation="${esc(c.id)}" data-title="${esc(c.title)}" title="${esc(c.title)} · ${c.message_count} lượt hỏi"><span>${esc(c.title)}</span></button><button class="delete-conversation icon-button" data-delete-conversation="${esc(c.id)}" data-title="${esc(c.title)}" aria-label="Xóa cuộc trò chuyện ${esc(c.title)}" title="Xóa cuộc trò chuyện">×</button></article>`;
  }).join('')||'<p class="history-empty">'+(historyQuery?'Không tìm thấy cuộc trò chuyện.':'Chưa có lịch sử. Bắt đầu với một chat mới.')+'</p>';
  selectConversation();
}
async function loadConversations(more=false){
  if(more&&historyLoading)return;
  const version=++historyVersion;
  if(!more){historyOffset=0;historyQuery=$('#history-search').value.trim()}
  historyLoading=true;$('#history-more').disabled=true;$('#history-status').textContent='Đang tải lịch sử…';
  try{
    const d=await api('/conversations?offset='+historyOffset+'&q='+encodeURIComponent(historyQuery));
    if(version!==historyVersion)return;
    historyItems=more?[...new Map([...historyItems,...d.items].map(c=>[c.id,c])).values()]:d.items;
    renderHistory();historyOffset=d.next_offset;$('#history-more').classList.toggle('hidden',!d.has_more);$('#history-status').textContent='';
  }catch(e){if(version===historyVersion)$('#history-status').textContent='Không tải được lịch sử. Nhấn ↻ để thử lại.';throw e}
  finally{if(version===historyVersion){historyLoading=false;$('#history-more').disabled=false}}
}
$('#refresh-history').onclick=()=>loadConversations().catch(e=>toast(e.message));
$('#history-more').onclick=()=>loadConversations(true).catch(e=>toast(e.message));
$('#history-search').oninput=()=>{clearTimeout(historySearchTimer);historyVersion++;$('#history-more').disabled=true;historySearchTimer=setTimeout(()=>loadConversations().catch(e=>toast(e.message)),250)};
document.addEventListener('click',e=>{const b=e.target.closest('[data-conversation]');if(b)openConversation(b.dataset.conversation,b.dataset.title).catch(e=>toast(e.message))});

let sidebarMobile=innerWidth<=600,sidebarClosed=sidebarMobile;
try{const saved=localStorage.getItem('cyberant-sidebar-closed');if(!sidebarMobile&&saved!==null)sidebarClosed=saved==='true'}catch{}
function setSidebar(closed){
  if(closed){$('#workspace main').inert=false;if($('#sidebar').contains(document.activeElement))$('#sidebar-toggle').focus()}
  sidebarClosed=closed;$('#workspace').classList.toggle('sidebar-closed',closed);$('#sidebar').inert=closed;
  $('#sidebar').setAttribute('aria-hidden',String(closed));$('#sidebar-toggle').setAttribute('aria-expanded',String(!closed));
  $('#sidebar-toggle').title=closed?'Mở thanh bên':'Thu gọn thanh bên';$('#sidebar-toggle').setAttribute('aria-label',$('#sidebar-toggle').title);
  $('#sidebar-backdrop').classList.toggle('hidden',closed||!sidebarMobile);
  $('#workspace main').inert=sidebarMobile&&!closed;
  if(!sidebarMobile)try{localStorage.setItem('cyberant-sidebar-closed',String(closed))}catch{}
}
$('#sidebar-toggle').onclick=()=>{setSidebar(!sidebarClosed);if(sidebarMobile&&!sidebarClosed)$('#new-chat').focus()};
$('#sidebar-backdrop').onclick=()=>{setSidebar(true);$('#sidebar-toggle').focus()};
window.addEventListener('resize',()=>{const mobile=innerWidth<=600;if(mobile!==sidebarMobile){sidebarMobile=mobile;setSidebar(mobile)}else setSidebar(sidebarClosed)});
document.addEventListener('keydown',e=>{
  if(e.key==='Escape'&&!$('#profile-menu').classList.contains('hidden')){setProfile(false);$('#profile-toggle').focus();return}
  if(e.key==='Escape'&&!sidebarClosed&&!$('dialog[open]')){setSidebar(true);$('#sidebar-toggle').focus()}
  if(e.key==='Tab'&&sidebarMobile&&!sidebarClosed&&!$('dialog[open]')){
    const items=$$('#sidebar button:not(:disabled), #sidebar input').filter(el=>el.getClientRects().length),first=items[0],last=items.at(-1);
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}
    else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}
  }
});
function setProfile(open){$('#profile-menu').classList.toggle('hidden',!open);$('#profile-toggle').setAttribute('aria-expanded',String(open))}
$('#profile-toggle').onclick=()=>setProfile($('#profile-menu').classList.contains('hidden'));
document.addEventListener('click',e=>{
  if(!e.target.closest('.profile')||e.target.closest('#profile-menu button'))setProfile(false);
  if(sidebarMobile&&e.target.closest('#sidebar [data-view]')){setSidebar(true);$('#sidebar-toggle').focus()}
});
setSidebar(sidebarClosed);

$('#older-messages').onclick=async()=>{
  if(busy||conversationLoading||!olderBefore)return;
  conversationLoading=true;updateChatControls();$('#older-messages').disabled=true;
  try{
    const panel=$('.chat-main'),height=panel.scrollHeight,top=panel.scrollTop;
    const d=await api('/conversations/'+currentConversation+'?before='+olderBefore);
    displayConversation([...d.messages,...loadedMessages]);olderBefore=d.next_before;$('#older-messages').classList.toggle('hidden',!d.has_more);
    panel.scrollTop=top+panel.scrollHeight-height;
  }catch(e){toast(e.message)}finally{conversationLoading=false;$('#older-messages').disabled=false;updateChatControls()}
};
document.addEventListener('click',async e=>{
  const b=e.target.closest('[data-delete-conversation]');if(!b)return;const id=b.dataset.deleteConversation;
  if(busy||conversationLoading){toast('Chờ thao tác hiện tại hoàn tất rồi xóa.');return}
  if(!confirm('Xóa cuộc trò chuyện “'+b.dataset.title+'” cùng tất cả câu hỏi, câu trả lời và phản hồi? Thao tác không có hoàn tác; bản sao lưu cũ không bị xóa.'))return;
  b.disabled=true;conversationLoading=true;updateChatControls();
  try{
    await api('/conversations/'+encodeURIComponent(id),{method:'DELETE'});
    if(currentConversation===id){currentConversation=null;displayConversation([]);olderBefore=null;$('#question').value='';$('#older-messages').classList.add('hidden');$('#conversation-title').textContent='Cuộc trò chuyện mới'}
    await loadConversations();toast('Đã xóa cuộc trò chuyện.');$('#refresh-history').focus();
  }catch(err){toast(err.message);b.disabled=false}finally{conversationLoading=false;updateChatControls()}
});
