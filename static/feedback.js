let reportChat=null,reportRating=-1,feedbackOffset=0,feedbackLoading=false;
const reviewLabels={new:'Mới',reviewing:'Đang rà soát',resolved:'Đã xử lý',dismissed:'Không xử lý'};
function openFeedback(chat,rating){
  reportChat=chat;reportRating=rating;$('#feedback-form').reset();
  $('#report-reason').disabled=rating===1;$('#feedback-modal').showModal();
}
$('#report-cancel').onclick=()=>$('#feedback-modal').close();
$('#feedback-form').onsubmit=async e=>{
  e.preventDefault();$('#report-submit').disabled=true;
  try{await api('/feedback',{method:'POST',body:JSON.stringify({chat_id:reportChat,rating:reportRating,reason:reportRating===1?'':$('#report-reason').value,comment:$('#report-comment').value})});$('#feedback-modal').close();toast('Đã ghi nhận phản hồi. Không tự đưa vào huấn luyện.')}
  catch(err){toast(err.message)}finally{$('#report-submit').disabled=false}
};
async function loadFeedback(more=false){
  if(feedbackLoading||currentUser?.role!=='admin')return;feedbackLoading=true;
  $('#feedback-loading').textContent='Đang tải phản hồi…';
  try{
    if(!more)feedbackOffset=0;
    const params=new URLSearchParams({offset:feedbackOffset,q:$('#feedback-search').value,status:$('#feedback-status').value,model:$('#feedback-model').value.trim(),reason:$('#feedback-reason').value});
    if($('#feedback-rating').value)params.set('rating',$('#feedback-rating').value);
    const data=await api('/admin/feedback?'+params);
    const html=data.items.map(r=>`<article class="card feedback-entry"><small>${esc(r.username||'Không có metadata')} · ${esc(r.model||'Không rõ model')} · ${esc(r.updated)}</small><h3>${esc(r.question)}</h3><p>${esc(reviewLabels[r.status])} · ${r.rating===1?'Hữu ích':r.rating===-1?'Báo sai':'Trung lập'} · ${esc(r.reason)}</p><button class="secondary" data-report="${r.id}">Xem và rà soát</button></article>`).join('');
    if(more)$('#feedback-list').insertAdjacentHTML('beforeend',html);else $('#feedback-list').innerHTML=html||'<p>Không có phản hồi phù hợp.</p>';
    feedbackOffset=data.next_offset;$('#feedback-more').classList.toggle('hidden',!data.has_more);
  }finally{feedbackLoading=false;$('#feedback-loading').textContent=''}
}
$('#feedback-filters').onsubmit=e=>{e.preventDefault();loadFeedback().catch(err=>toast(err.message))};
$('#feedback-more').onclick=()=>loadFeedback(true).catch(err=>toast(err.message));
async function showFeedback(id){
  const r=await api('/admin/feedback/'+id),s=r.snapshot,panel=$('#feedback-detail');
  panel.innerHTML=`<h2>Phản hồi #${r.id}</h2><p>${esc(s.username)} · Chat ${esc(s.chat_id)} · Hội thoại ${esc(s.conversation_id)}</p><h3>Câu hỏi</h3><p>${esc(s.question)}</p><h3>Câu trả lời hiển thị</h3><div class="message-text">${renderAnswer(s.answer||'Thiếu metadata')}</div><p>Ghi chú: ${esc(r.comment)}</p><details><summary>Model, usage, nguồn và chẩn đoán</summary><pre>${esc(JSON.stringify(s,null,2))}</pre></details><details><summary>Lịch sử thay đổi đánh giá</summary><pre>${esc(JSON.stringify(r.history,null,2))}</pre></details><form id="feedback-review" class="auth-fields"><label>Trạng thái<select id="review-status">${Object.entries(reviewLabels).map(([key,label])=>`<option value="${key}" ${key===r.status?'selected':''}>${label}</option>`).join('')}</select></label><label>Ghi chú admin<textarea id="review-note" maxlength="2000" rows="3">${esc(r.note)}</textarea></label><button class="primary">Lưu rà soát</button><button id="purge-feedback" type="button" class="secondary">Xóa phản hồi và lịch sử</button></form>`;
  panel.classList.remove('hidden');panel.scrollIntoView({block:'start'});
  $('#feedback-review').onsubmit=async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;try{await api('/admin/feedback/'+id,{method:'PUT',body:JSON.stringify({status:$('#review-status').value,note:$('#review-note').value})});await loadFeedback();await showFeedback(id);toast('Đã lưu rà soát.')}catch(err){toast(err.message)}finally{button.disabled=false}};
  $('#purge-feedback').onclick=async()=>{if(!confirm('Xóa vĩnh viễn phản hồi và lịch sử này? Hội thoại và usage vẫn giữ; bản sao lưu cũ không bị xóa.'))return;try{await api('/admin/feedback/'+id,{method:'DELETE'});panel.classList.add('hidden');panel.textContent='';await loadFeedback()}catch(err){toast(err.message)}};
}
document.addEventListener('click',e=>{const b=e.target.closest('[data-report]');if(b)showFeedback(b.dataset.report).catch(err=>toast(err.message))});
window.addEventListener('focus',()=>{if(currentUser&&!busy)checkHealth()});
