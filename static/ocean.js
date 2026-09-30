// Bounded native Canvas effect: 30 fps, capped DPR, no animation off-screen or on low-power devices.
(()=>{
  const canvas=document.querySelector('#ocean'),login=document.querySelector('#login'),ctx=canvas.getContext('2d');
  if(!ctx)return;
  const reduced=matchMedia('(prefers-reduced-motion: reduce)'),coarse=matchMedia('(pointer: coarse)');
  const lowPower=(navigator.deviceMemory&&navigator.deviceMemory<=4)||(navigator.hardwareConcurrency&&navigator.hardwareConcurrency<=4)||navigator.connection?.saveData;
  let width=0,height=0,frame=0,last=0,pointer={x:.3,y:.55},ripples=[],lastRipple=0;
  function resize(){
    width=login.clientWidth;height=login.clientHeight;
    const scale=Math.min(devicePixelRatio||1,1.5,1600/Math.max(width,1));
    canvas.width=Math.round(width*scale);canvas.height=Math.round(height*scale);ctx.setTransform(scale,0,0,scale,0,0);
    sync();
  }
  function draw(time){
    const dark=document.documentElement.dataset.theme==='dark';
    ctx.clearRect(0,0,width,height);
    const glow=ctx.createRadialGradient(pointer.x*width,pointer.y*height,0,pointer.x*width,pointer.y*height,width*.7);
    glow.addColorStop(0,dark?'rgba(27,148,181,.24)':'rgba(95,215,227,.33)');glow.addColorStop(1,'rgba(20,110,150,0)');
    ctx.fillStyle=glow;ctx.fillRect(0,0,width,height);
    for(let row=0;row<22;row++){
      ctx.beginPath();
      for(let x=0;x<=width+24;x+=24){
        const y=height*.47+row*height*.028+Math.sin(x/190+time*.00024+row*.19)*24+Math.cos(x/310-time*.00017+row*.3)*18;
        if(x===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
      }
      ctx.strokeStyle=dark?`rgba(88,199,217,${.05+row*.004})`:`rgba(29,120,155,${.06+row*.003})`;ctx.lineWidth=1;ctx.stroke();
    }
    ripples=ripples.filter(r=>time-r.time<1600);
    ripples.forEach(r=>{
      const age=(time-r.time)/1600;
      ctx.beginPath();ctx.ellipse(r.x,r.y,12+age*160,6+age*55,0,0,Math.PI*2);
      ctx.strokeStyle=`rgba(104,204,220,${(1-age)*.45})`;ctx.stroke();
    });
  }
  function enabled(){return !document.hidden&&!login.classList.contains('hidden')&&!reduced.matches&&!coarse.matches&&!lowPower}
  function tick(time){
    if(!enabled()){frame=0;return}
    if(time-last>=33){draw(time);last=time}
    frame=requestAnimationFrame(tick);
  }
  function sync(){cancelAnimationFrame(frame);frame=0;ripples=[];draw(0);if(enabled())frame=requestAnimationFrame(tick)}
  login.addEventListener('pointermove',e=>{
    if(!enabled())return;
    const box=login.getBoundingClientRect();pointer={x:(e.clientX-box.left)/width,y:(e.clientY-box.top)/height};
    const time=performance.now();if(time-lastRipple>180){ripples.push({x:e.clientX-box.left,y:e.clientY-box.top,time});ripples=ripples.slice(-8);lastRipple=time}
  },{passive:true});
  login.addEventListener('pointerleave',()=>{pointer={x:.3,y:.55}},{passive:true});
  document.addEventListener('visibilitychange',sync);document.addEventListener('themechange',sync);
  reduced.addEventListener('change',sync);coarse.addEventListener('change',sync);
  new MutationObserver(sync).observe(login,{attributes:true,attributeFilter:['class']});
  new ResizeObserver(resize).observe(login);resize();
})();
