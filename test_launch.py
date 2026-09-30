"""Real entrypoint on a temporary database; no provider requests."""
import ast,os,socket,sqlite3,subprocess,sys,time
from pathlib import Path
import httpx
import pytest
ROOT=Path(__file__).resolve().parent

def settings(tmp_path):
    return {**os.environ,'APP_DATA_DIR':str(tmp_path/'data'),'APP_ENV':'lan',
        'APP_ORIGINS':'http://127.0.0.1:8088','BOOTSTRAP_ADMIN_PASSWORD':'Launch-password-12345',
        'BOOTSTRAP_ADMIN_USERNAME':'admin','PYTHONDONTWRITEBYTECODE':'1'}

def test_real_start_duplicate_restart_and_preserved_data(tmp_path):
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    env=settings(tmp_path);env['APP_ORIGINS']=f'http://127.0.0.1:{port}'
    command=[sys.executable,str(ROOT/'main.py'),'--host','127.0.0.1','--port',str(port)]
    def start():
        process=subprocess.Popen(command,cwd=tmp_path,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            try:
                if httpx.get(f'http://127.0.0.1:{port}/api/health',trust_env=False,timeout=1).status_code==200:return process
            except httpx.HTTPError:pass
            if process.poll() is not None:pytest.fail('Temporary server exited during startup')
            time.sleep(.2)
        process.kill();process.wait();pytest.fail('Temporary server startup timeout')
    process=start()
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False) as c:
            assert c.get('/').status_code==200
            assert c.post('/api/login',json={'username':'admin','password':env['BOOTSTRAP_ADMIN_PASSWORD']}).status_code==200
            assert c.get('/api/admin/feedback').status_code==200
            conversation=c.post('/api/conversations').json()['id']
        path=tmp_path/'data/app.sqlite3'
        with sqlite3.connect(path) as db:before=db.execute('SELECT * FROM users').fetchall()
        duplicate=subprocess.run(command,cwd=tmp_path,env=env,capture_output=True,text=True,timeout=30)
        assert duplicate.returncode!=0 and 'Cannot listen' in duplicate.stderr
        with sqlite3.connect(path) as db:assert db.execute('SELECT * FROM users').fetchall()==before
    finally:process.terminate();process.wait(timeout=30)
    process=start()
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False) as c:
            assert c.post('/api/login',json={'username':'admin','password':env['BOOTSTRAP_ADMIN_PASSWORD']}).status_code==200
            assert c.get('/api/conversations/'+conversation).status_code==200
        with sqlite3.connect(path) as db:
            assert db.execute('SELECT * FROM users').fetchall()==before
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    finally:process.terminate();process.wait(timeout=30)

@pytest.mark.parametrize('arguments',[['--port','0'],['--port','65536'],['--port','no']])
def test_bad_port_has_no_database_side_effects(tmp_path,arguments):
    result=subprocess.run([sys.executable,str(ROOT/'main.py'),*arguments],env=settings(tmp_path),capture_output=True,timeout=30)
    assert result.returncode!=0 and not (tmp_path/'data').exists()


def test_docker_context_includes_all_local_runtime_imports():
    rules=(ROOT/'.dockerignore').read_text().splitlines()
    pending=['app','main'];seen=set()
    while pending:
        name=pending.pop()
        if name in seen:continue
        seen.add(name);assert '!'+name+'.py' in rules,name
        tree=ast.parse((ROOT/(name+'.py')).read_text(encoding='utf8'))
        for node in ast.walk(tree):
            modules=[n.name for n in node.names] if isinstance(node,ast.Import) else [node.module] if isinstance(node,ast.ImportFrom) else []
            pending.extend(m for m in modules if m and (ROOT/(m+'.py')).is_file())
