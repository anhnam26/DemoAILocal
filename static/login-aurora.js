// Login-only enhancement: CSS supplies the static fallback and both theme palettes.
(()=>{
  const login=document.querySelector('#login'),aurora=login?.querySelector('.login-aurora');
  if(!aurora)return;
  const reduced=matchMedia('(prefers-reduced-motion: reduce)'),pointer=matchMedia('(hover: hover) and (pointer: fine)');
  let cells=[],frame=0,last=0,bounds=null;
  const active=()=>!reduced.matches&&pointer.matches&&!document.hidden&&!login.classList.contains('hidden');
  function reset(){
    cancelAnimationFrame(frame);frame=0;last=0;bounds=null;
    cells.forEach(cell=>cell.el.remove());cells=[];
  }
  function prepare(){
    if(bounds)return;
    bounds=login.getBoundingClientRect();
    const columns=Math.min(20,Math.max(1,Math.ceil(bounds.width/120))),rows=Math.min(16,Math.max(1,Math.ceil(bounds.height/120)));
    const fragment=document.createDocumentFragment();
    for(let row=0;row<rows;row++)for(let column=0;column<columns;column++){
      const el=document.createElement('span'),x=(column+.5)/columns,y=(row+.5)/rows;
      el.className='aurora-cell';
      // Overlapping, fixed patches: only their colour intensity ever changes.
      el.style.left=`${(column-.5)/columns*100}%`;el.style.top=`${(row-.5)/rows*100}%`;
      el.style.width=`${200/columns}%`;el.style.height=`${200/rows}%`;
      cells.push({el,x:x*bounds.width,y:y*bounds.height,value:0,target:0});fragment.append(el);
    }
    aurora.append(fragment);
  }
  function draw(now){
    frame=0;
    if(!active()){reset();return}
    const elapsed=Math.min(last?now-last:16,64);last=now;
    let settled=true;
    for(const cell of cells){
      if(cell.value===cell.target)continue;
      cell.value+=(cell.target-cell.value)*(1-Math.exp(-elapsed/(cell.target>cell.value?85:380)));
      if(Math.abs(cell.target-cell.value)<.003)cell.value=cell.target;else settled=false;
      cell.el.style.opacity=cell.value.toFixed(3);
    }
    if(!settled)frame=requestAnimationFrame(draw);else last=0;
  }
  function start(){if(!frame&&active())frame=requestAnimationFrame(draw)}
  login.addEventListener('pointermove',event=>{
    if(event.pointerType==='touch'||!active())return;
    prepare();
    const box=login.getBoundingClientRect(),x=event.clientX-box.left,y=event.clientY-box.top;
    for(const cell of cells){
      const distance=Math.hypot(cell.x-x,cell.y-y),weight=Math.max(0,1-distance/180);
      cell.target=weight*weight*(3-2*weight);
    }
    start();
  },{passive:true});
  login.addEventListener('pointerleave',()=>{cells.forEach(cell=>cell.target=0);if(cells.length)start()},{passive:true});
  login.addEventListener('pointercancel',reset,{passive:true});
  window.addEventListener('blur',reset);
  window.addEventListener('resize',reset,{passive:true});
  document.addEventListener('visibilitychange',reset);
  reduced.addEventListener('change',reset);pointer.addEventListener('change',reset);
  new MutationObserver(reset).observe(login,{attributes:true,attributeFilter:['class']});
})();
