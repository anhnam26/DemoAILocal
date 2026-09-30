"""Bash launcher contract using fake Conda; also runs on Git Bash/Windows."""
import os,shutil,subprocess
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parent
BASH=shutil.which('bash') if os.name!='nt' else r'C:\Program Files\Git\bin\bash.exe'
pytestmark=pytest.mark.skipif(not BASH or not Path(BASH).exists(),reason='Bash unavailable')

def shell_path(path):
    value=Path(path).resolve().as_posix()
    return '/'+value[0].lower()+value[2:] if os.name=='nt' else value

def run(script,env,*args):
    return subprocess.run([BASH,shell_path(script),*args],env=env,capture_output=True,text=True,timeout=20)

def setup(tmp_path):
    project=tmp_path/'source with spaces';project.mkdir()
    shutil.copyfile(ROOT/'start.sh',project/'start.sh')
    (project/'.env').write_text('KEEP=unchanged\n')
    base=tmp_path/'fake conda';(base/'etc/profile.d').mkdir(parents=True);(base/'bin').mkdir()
    executable=base/'bin/conda'
    executable.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$FAKE_BASE"\n',newline='\n');executable.chmod(0o755)
    (base/'etc/profile.d/conda.sh').write_text('''conda() {
    [[ "$1" == activate && "$2" == cyberant ]] || return 9
    [[ "${FAIL_ACTIVATE:-0}" == 0 ]] || return 8
    export CONDA_PREFIX="$FAKE_BASE/env"
}
''',newline='\n')
    (base/'env/bin').mkdir(parents=True)
    python=base/'env/bin/python';python.write_text('''#!/usr/bin/env bash
printf 'CWD=%s\\n' "$PWD"
printf 'ARG=%s\\n' "$@"
exit "${FAKE_EXIT:-0}"
''',newline='\n');python.chmod(0o755)
    env={**os.environ,'CONDA_EXE':shell_path(executable),'FAKE_BASE':shell_path(base)}
    return project,env

def test_syntax_and_help():
    r=subprocess.run([BASH,'-n',shell_path(ROOT/'start.sh')],capture_output=True,timeout=20);assert r.returncode==0
    assert run(ROOT/'start.sh',os.environ,'--help').returncode==0

def test_activation_paths_arguments_and_exit_code(tmp_path):
    project,env=setup(tmp_path)
    r=run(project/'start.sh',env,'--port','8090');assert r.returncode==0,r.stderr
    assert 'CWD='+shell_path(project) in r.stdout
    assert 'ARG='+shell_path(project)+'/main.py' in r.stdout
    assert 'ARG=0.0.0.0' in r.stdout and 'ARG=8088' in r.stdout and 'ARG=8090' in r.stdout
    assert (project/'.env').read_text()=='KEEP=unchanged\n'
    assert run(project/'start.sh',{**env,'FAKE_EXIT':'7'}).returncode==7

def test_missing_conda_environment_and_configuration(tmp_path):
    project,env=setup(tmp_path)
    assert 'Cannot activate' in run(project/'start.sh',{**env,'FAIL_ACTIVATE':'1'}).stderr
    assert 'Conda not found' in run(project/'start.sh',{**env,'CONDA_EXE':'/missing/conda'}).stderr
    (project/'.env').unlink()
    assert 'Missing .env' in run(project/'start.sh',env).stderr
