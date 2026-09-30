// Runs before styles to avoid a flash of the wrong theme. No inline scripts/CSP exceptions.
(()=>{
  const system=matchMedia('(prefers-color-scheme: dark)');
  let preference=null;
  try{preference=localStorage.getItem('cyberant-theme')}catch{}
  function apply(){
    const dark=preference==='dark'||(preference!=='light'&&system.matches);
    document.documentElement.dataset.theme=dark?'dark':'light';
    document.querySelectorAll('[data-theme-toggle]').forEach(button=>{
      button.textContent=dark?'☀':'☾';
      button.setAttribute('aria-label',dark?'Chuyển sang giao diện sáng':'Chuyển sang giao diện tối');
      button.title=button.getAttribute('aria-label');button.setAttribute('aria-pressed',String(dark));
    });
    document.dispatchEvent(new Event('themechange'));
  }
  apply();document.addEventListener('DOMContentLoaded',apply);system.addEventListener('change',apply);
  document.addEventListener('click',e=>{
    if(!e.target.closest('[data-theme-toggle]'))return;
    preference=document.documentElement.dataset.theme==='dark'?'light':'dark';
    try{localStorage.setItem('cyberant-theme',preference)}catch{}
    apply();
  });
  window.addEventListener('storage',e=>{if(e.key==='cyberant-theme'||e.key===null){preference=e.newValue;apply()}});
})();
