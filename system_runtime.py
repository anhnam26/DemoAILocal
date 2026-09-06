"""Real local telemetry and narrowly scoped control of this workspace's model process."""
from pathlib import Path
import json,os,time,subprocess,threading,platform,shutil
import psutil,httpx
ROOT=Path(__file__).parent
CONFIG=ROOT/'data'/'runtime-config.json'
DEFAULT=dict(context=4096,gpu_layers=99,cache_ram=256,temperature=0.2,max_tokens=800)
BOOT=time.time();ACTION={'state':'idle'};MUTEX=threading.Lock();METRICS={};METRICS_TIME=0

def config():
    return {**DEFAULT,**(json.loads(CONFIG.read_text(encoding='utf8')) if CONFIG.exists() else {})}
def save_config(value):
    temp=CONFIG.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2),encoding='utf8');temp.replace(CONFIG)
def headers():
    path=ROOT/'data'/'model-api-key.txt';return {'Authorization':'Bearer '+path.read_text(encoding='utf8').strip()} if path.exists() else {}
def model_processes():
    result=[];target=(ROOT/'runtime'/'llama-server.exe').resolve()
    for p in psutil.process_iter(['name','exe','cmdline']):
        try:
            if p.info['exe'] and Path(p.info['exe']).resolve()==target and 'cyberant-qwen3.5-9b' in (p.info['cmdline'] or []):result.append(p)
        except (psutil.Error,OSError):pass
    return result
def observed_config():
    processes=model_processes()
    if not processes:return None
    args=processes[0].cmdline();result={}
    for flag,key in [('--ctx-size','context'),('--gpu-layers','gpu_layers'),('--parallel','parallel'),('--cache-ram','cache_ram'),('--port','port')]:
        try:result[key]=int(args[args.index(flag)+1])
        except (ValueError,IndexError):result[key]=None
    result.update(pid=processes[0].pid,device='Vulkan GPU',host='127.0.0.1');return result
def gpu_metrics():
    exe=shutil.which('nvidia-smi')
    if not exe:return dict(available=False,reason='Không tìm thấy nvidia-smi; không suy đoán VRAM.')
    try:
        r=subprocess.run([exe,'--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu,power.draw,driver_version','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=4,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if r.returncode:raise ValueError('NVIDIA không cung cấp số đo')
        rows=[]
        def number(x):
            try:return float(x.strip())
            except ValueError:return None
        for row in r.stdout.strip().splitlines():
            a=[x.strip() for x in row.split(',')]
            if len(a)>=7:rows.append(dict(name=a[0],total_mib=number(a[1]),used_mib=number(a[2]),utilization=number(a[3]),temperature=number(a[4]),power_w=number(a[5]),driver=a[6]))
        return dict(available=bool(rows),devices=rows,note='VRAM là tổng sử dụng GPU toàn máy, không chỉ riêng model. N/A hiển thị chưa đo được.')
    except (OSError,ValueError,subprocess.TimeoutExpired) as e:return dict(available=False,reason=str(e))
def metrics():
    global METRICS,METRICS_TIME
    if time.time()-METRICS_TIME<3 and METRICS:return METRICS
    vm=psutil.virtual_memory();swap=psutil.swap_memory();net=psutil.net_io_counters();disk=psutil.disk_usage(str(ROOT))
    processes=[]
    for p in [psutil.Process(os.getpid())]+model_processes():
        try:
            m=p.memory_info();processes.append(dict(pid=p.pid,name=p.name(),rss=m.rss,private=getattr(m,'private',m.vms),started=p.create_time(),threads=p.num_threads()))
        except psutil.Error:pass
    connections=[]
    try:
        for c in psutil.net_connections(kind='tcp'):
            if c.laddr and c.laddr.port in (8088,1234):connections.append(dict(local=f'{c.laddr.ip}:{c.laddr.port}',status=c.status,pid=c.pid))
    except psutil.Error:pass
    METRICS=dict(measured_at=time.time(),cpu=dict(percent=psutil.cpu_percent(interval=.1),logical=psutil.cpu_count(),physical=psutil.cpu_count(logical=False)),ram=dict(total=vm.total,available=vm.available,used=vm.total-vm.available,percent=vm.percent),swap=dict(total=swap.total,used=swap.used,percent=swap.percent),disk=dict(path=ROOT.anchor,total=disk.total,free=disk.free,used=disk.used,percent=disk.percent),network=dict(sent=net.bytes_sent,received=net.bytes_recv,note='Bộ đếm lưu lượng toàn máy; không phải thống kê riêng ứng dụng.'),gpu=gpu_metrics(),processes=processes,connections=connections,uptime=time.time()-BOOT,platform=platform.platform(),python=platform.python_version(),configured=config(),observed=observed_config(),action=dict(ACTION))
    METRICS_TIME=time.time();return METRICS
def model_args(c):
    return [str(ROOT/'runtime'/'llama-server.exe'),'-m',str(ROOT/'models'/'Qwen3.5-9B-Q4_K_M.gguf'),'--alias','cyberant-qwen3.5-9b','--device','Vulkan0','--gpu-layers',str(c['gpu_layers']),'--ctx-size',str(c['context']),'--parallel','1','--flash-attn','on','--cache-type-k','q8_0','--cache-type-v','q8_0','--batch-size','256','--ubatch-size','128','--cache-ram',str(c['cache_ram']),'--host','127.0.0.1','--port','1234','--api-key-file',str(ROOT/'data'/'model-api-key.txt'),'--cors-origins','http://127.0.0.1:8088','--no-webui','--log-verbosity','4']
def control(action):
    # Called under application generation semaphore; only our exact executable/alias can be stopped.
    global ACTION,METRICS_TIME
    ACTION=dict(state='running',action=action,started=time.time());METRICS_TIME=0
    try:
        processes=model_processes()
        if action in ('stop','restart'):
            for p in processes:p.terminate()
            _,alive=psutil.wait_procs(processes,timeout=8)
            if alive:raise RuntimeError('Model chưa dừng; không khởi tạo tiến trình trùng.')
        if action in ('start','restart'):
            if action=='start' and processes:
                ACTION=dict(state='done',action=action,message='Model đã chạy.');return
            for c in psutil.net_connections(kind='tcp'):
                if c.laddr and c.laddr.port==1234 and c.status=='LISTEN':raise RuntimeError('Cổng 1234 đang do dịch vụ khác giữ; không dừng dịch vụ đó.')
            logs=ROOT/'logs';logs.mkdir(exist_ok=True)
            with (logs/'model.stdout.log').open('ab') as out,(logs/'model.stderr.log').open('ab') as err:
                p=subprocess.Popen(model_args(config()),cwd=ROOT,stdout=out,stderr=err,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            ready=False
            with httpx.Client(timeout=2,trust_env=False) as client:
                for _ in range(90):
                    if p.poll() is not None:raise RuntimeError('Model thoát khi nạp; đọc nhật ký trong tab hệ thống.')
                    try:
                        r=client.get('http://127.0.0.1:1234/v1/models',headers=headers());ready=r.status_code==200
                    except httpx.HTTPError:pass
                    if ready:break
                    time.sleep(1)
            if not ready:raise RuntimeError('Model còn nạp sau 90 giây; xem trạng thái và log, không tạo thêm tiến trình.')
        ACTION=dict(state='done',action=action,message='Đã '+{'start':'khởi động','stop':'dừng','restart':'khởi động lại'}[action]+' model.',finished=time.time())
    except Exception as e:ACTION=dict(state='error',action=action,message=str(e),finished=time.time())
    finally:METRICS_TIME=0

if __name__=='__main__':
    import sys
    if sys.argv[1:] and sys.argv[1]=='start':control('start');print(json.dumps(ACTION,ensure_ascii=True))
