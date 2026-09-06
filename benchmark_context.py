"""Explicit maintenance benchmark. Stops this demo, restores it in finally.
Tests GPU allocation and a near-full token prompt; never assumes token count from characters.
"""
from pathlib import Path
import subprocess,time,json,os
import httpx,psutil
import system_runtime as runtime
ROOT=Path(__file__).parent
FLAGS=getattr(subprocess,'CREATE_NO_WINDOW',0)
REPORT=ROOT/'artifacts'/'context-benchmark.json'

def run():
    original=runtime.config();report=dict(started=time.strftime('%Y-%m-%d %H:%M:%S'),original=original,trials=[],native_context=262144,note='One GPU slot, Q4_K_M weights, Q8 KV; allocation and near-full repeated-token prompt are distinct tests. Not a semantic quality benchmark.')
    REPORT.parent.mkdir(exist_ok=True)
    def save():REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
    subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Stop-Demo.ps1')],cwd=ROOT,creationflags=FLAGS,check=True,capture_output=True)
    p=None
    try:
        for context in (8192,16384,32768,65536,98304,131072,196608,262144):
            trial=dict(context=context,parallel=1);report['trials'].append(trial);save()
            if psutil.virtual_memory().available<768*1024**2:
                trial.update(state='skipped_ram_guard',available_ram=psutil.virtual_memory().available);break
            prior=[t for t in report['trials'][:-1] if t.get('state')=='allocated']
            if len(prior)>=2:
                a,b=prior[-2:];slope=(b['vram_used_mib']-a['vram_used_mib'])/(b['context']-a['context'])
                projected=b['vram_used_mib']+max(0,slope)*(context-b['context'])
                if projected>b['vram_total_mib']-384:
                    trial.update(state='skipped_vram_guard',projected_used_mib=round(projected),headroom_mib=384);break
            c={**original,'context':context,'parallel':1}
            log=ROOT/'logs'/f'context-{context}.log'
            with log.open('wb') as f:
                p=subprocess.Popen(runtime.model_args(c)+['--fit','off','--no-context-shift'],cwd=ROOT,stdout=f,stderr=f,creationflags=FLAGS)
            try:
                start=time.monotonic()
                with httpx.Client(base_url='http://127.0.0.1:1234',headers=runtime.headers(),trust_env=False,timeout=4) as client:
                    while time.monotonic()-start<100:
                        if p.poll() is not None:raise RuntimeError('Model exited during allocation')
                        try:
                            ready=client.get('/v1/models').status_code==200
                            if ready:break
                        except httpx.HTTPError:pass
                        time.sleep(.5)
                    else:raise RuntimeError('Model startup timeout')
                    slots=client.get('/slots').json();trial['slots']=len(slots)
                    # Parse actual runtime log; startup flags alone are insufficient evidence.
                    text=log.read_text(encoding='utf8',errors='replace')
                    import re
                    match=re.search(r'n_ctx_seq\s*=\s*(\d+)',text)
                    assert match and int(match[1])==context and 'offloaded 33/33 layers to GPU' in text
                    gpu=runtime.gpu_metrics()['devices'][0]
                    trial.update(state='allocated',load_seconds=round(time.monotonic()-start,2),vram_used_mib=gpu['used_mib'],vram_total_mib=gpu['total_mib'],actual_context=context,offloaded='33/33')
                    probe=client.post('/completion',json=dict(prompt='Reply briefly: what is a computer network?',n_predict=16,temperature=0),timeout=60);probe.raise_for_status()
                    trial['short_probe_tokens']=probe.json().get('tokens_predicted')
                    # Test full occupancy only at latest candidate below 64k to bound runtime.
                    if context>=32768:
                        token=client.post('/tokenize',json={'content':' data','add_special':False}).json()['tokens'][0]
                        tokens=[token]*(context-256)
                        t=time.monotonic();r=client.post('/completion',json=dict(prompt=tokens,n_predict=32,temperature=0,cache_prompt=False),timeout=480);r.raise_for_status();d=r.json()
                        trial['long_prompt']=dict(requested_tokens=len(tokens),evaluated_tokens=d.get('tokens_evaluated'),predicted_tokens=d.get('tokens_predicted'),seconds=round(time.monotonic()-t,2),truncated=d.get('truncated'),timings=d.get('timings'))
                        assert d.get('tokens_evaluated',0)>=len(tokens) and not d.get('truncated'), 'Prompt was truncated'
                        trial['long_passed']=True
                    print(json.dumps(trial,ensure_ascii=True),flush=True);save()
            except Exception as e:
                trial.update(state='failed',error=type(e).__name__+': '+str(e));print(json.dumps(trial,ensure_ascii=True),flush=True);save();break
            finally:
                if p and p.poll() is None:p.terminate();p.wait(timeout=15)
                p=None
            if trial.get('vram_total_mib',8192)-trial.get('vram_used_mib',0)<512:break
        report['max_allocated']=max((t['context'] for t in report['trials'] if t.get('state')=='allocated'),default=0)
        report['max_long_tested']=max((t['context'] for t in report['trials'] if t.get('long_passed')),default=0)
    finally:
        if p and p.poll() is None:p.terminate();p.wait(timeout=15)
        report['finished']=time.strftime('%Y-%m-%d %H:%M:%S');save()
        subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Start-Demo.ps1')],cwd=ROOT,creationflags=FLAGS,capture_output=True,timeout=60)
        print('Original saved configuration restarted; report in artifacts/context-benchmark.json',flush=True)
if __name__=='__main__':run()
