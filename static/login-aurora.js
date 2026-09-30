// Login-only enhancement: CSS supplies the static fallback and both theme palettes.
(()=>{
  const login=document.querySelector('#login'),glow=login?.querySelector('.aurora-glow'),sheen=login?.querySelector('.aurora-sheen');
  if(!glow||!sheen)return;
  const reduced=matchMedia('(prefers-reduced-motion: reduce)'),pointer=matchMedia('(hover: hover) and (pointer: fine)');
  const home={x:.38,y:.5};
  let current={...home},target={...home},frame=0,last=0,bounds=null;
  const active=()=>!reduced.matches&&pointer.matches&&!document.hidden&&!login.classList.contains('hidden');
  function reset(){
    cancelAnimationFrame(frame);frame=0;last=0;current={...home};target={...home};bounds=null;
    glow.style.removeProperty('transform');sheen.style.removeProperty('transform');
  }
  function draw(now){
    frame=0;
    if(!active()){reset();return}
    const mix=1-Math.exp(-Math.min(last?now-last:16,64)/110);last=now;
    current.x+=(target.x-current.x)*mix;current.y+=(target.y-current.y)*mix;
    const settled=Math.abs(target.x-current.x)+Math.abs(target.y-current.y)<.0004;
    if(settled)current={...target};
    const x=(current.x-home.x)*bounds.width,y=(current.y-home.y)*bounds.height;
    glow.style.transform=`translate3d(${(x*.7).toFixed(2)}px,${(y*.7).toFixed(2)}px,0)`;
    sheen.style.transform=`translate3d(${(-x*.08).toFixed(2)}px,${(-y*.08).toFixed(2)}px,0)`;
    if(!settled)frame=requestAnimationFrame(draw);else last=0;
  }
  function start(){if(!frame&&active()){bounds=login.getBoundingClientRect();frame=requestAnimationFrame(draw)}}
  login.addEventListener('pointermove',event=>{
    if(event.pointerType==='touch'||!active())return;
    bounds=login.getBoundingClientRect();
    target={x:Math.max(0,Math.min(1,(event.clientX-bounds.left)/bounds.width)),y:Math.max(0,Math.min(1,(event.clientY-bounds.top)/bounds.height))};
    start();
  },{passive:true});
  login.addEventListener('pointerleave',()=>{target={...home};start()},{passive:true});
  login.addEventListener('pointercancel',reset,{passive:true});
  window.addEventListener('blur',reset);
  window.addEventListener('resize',reset,{passive:true});
  document.addEventListener('visibilitychange',reset);
  reduced.addEventListener('change',reset);pointer.addEventListener('change',reset);
  new MutationObserver(reset).observe(login,{attributes:true,attributeFilter:['class']});
})();
