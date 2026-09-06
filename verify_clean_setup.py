"""Validate documented setup in a fresh source tree and Python environment; no model restart."""
from pathlib import Path
import tempfile,subprocess,shutil,json,sys
ROOT=Path(__file__).parent
def run(args,cwd,timeout=180):
    p=subprocess.run(args,cwd=cwd,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=timeout)
    if p.returncode:raise RuntimeError(str(args[:3])+' failed:\n'+p.stderr[-3500:]+'\n'+p.stdout[-1500:])
    return p.stdout
with tempfile.TemporaryDirectory(prefix='cyberant-setup-') as directory:
    target=Path(directory)
    tracked=run(['git','ls-files','-z'],ROOT).split('\0')
    for name in filter(None,tracked):
        source=ROOT/name
        if name.startswith(('data/','models/','logs/','artifacts/','backups/','exports/')) or not source.is_file():continue
        dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    run(['uv','venv','--python',sys.executable,'.venv-runtime'],target)
    python=target/'.venv-runtime/Scripts/python.exe'
    print('Created new Python environment; installing requirements-lock.txt.',flush=True)
    run(['uv','pip','install','--python',str(python),'-r','requirements-lock.txt'],target,300)
    run(['uv','pip','check','--python',str(python)],target)
    for script in ('company_data.py','security_data.py','finance_data.py','workflow_data.py'):
        run([str(python),'-X','utf8',script],target)
    run([str(python),'-X','utf8','-c','import app'],target)
    probe=target/'setup_probe.py'
    probe.write_text('''import app
from fastapi.testclient import TestClient
from testing_accounts import credentials
with TestClient(app.app) as c:
    assert c.get('/').status_code==200
    assert c.post('/api/login',json=credentials('sale')).status_code==200
    assert len(c.get('/api/documents').json())==481
    q=c.post('/api/chat',json={'question':'Firewall và WAF khác nhau như thế nào?'})
    assert q.status_code==200 and q.json()['sources']
    id=q.json()['conversation_id']
    assert c.get('/api/conversations/'+id).status_code==200
    assert c.delete('/api/conversations/'+id).status_code==200
    c.post('/api/logout')
    assert c.post('/api/login',json=credentials('admin')).status_code==200
    assert len(c.get('/api/admin/users').json()['users'])==3
print('Fresh dependencies, 481 documents, login, structured chat, history/delete and admin passed.')
''',encoding='utf8')
    print(run([str(python),'-X','utf8',str(probe)],target),flush=True)
report=dict(passed=True,fresh_environment=True,dependency_check=True,documents=481,accounts=3,checked=['seed scripts in order','app initialization','login','shared knowledge','structured chat','history delete','admin users'],limits='Did not re-download GGUF or restart GPU model; browser/GPU were verified in earlier runtime tests.')
(ROOT/'artifacts').mkdir(exist_ok=True)
(ROOT/'artifacts/setup-verification.json').write_text(json.dumps(report,indent=2),encoding='utf8')
