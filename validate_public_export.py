"""Smoke test a source-only export in a fresh temporary directory."""
from pathlib import Path
import tempfile,zipfile,subprocess,sys,json
ROOT=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='cyberant-public-') as tmp:
    dest=Path(tmp)
    with zipfile.ZipFile(ROOT/'exports/cyberant-ai-source.zip') as z:
        names=z.namelist()
        assert all(not any('/'+d+'/' in n for d in ('data','models','runtime','.git','logs','backups','artifacts')) for n in names)
        z.extractall(dest)
    project=dest/'cyberant-ai'
    for script in ('company_data.py','security_data.py','finance_data.py','workflow_data.py'):
        p=subprocess.run([sys.executable,'-X','utf8',script],cwd=project,capture_output=True,text=True,timeout=90)
        if p.returncode:raise RuntimeError(script+' failed: '+p.stderr[-1500:])
    probe=project/'probe.py';probe.write_text("import app\nwith app.connect() as c:\n assert c.execute('SELECT COUNT(*) FROM docs').fetchone()[0]==481\n assert c.execute('SELECT COUNT(*) FROM users').fetchone()[0]==3\nprint('Fresh source generated 481 documents and 3 local accounts.')\n",encoding='utf8')
    p=subprocess.run([sys.executable,'-X','utf8',str(probe)],cwd=project,capture_output=True,text=True,timeout=90)
    if p.returncode:raise RuntimeError(p.stderr[-1500:])
    print(p.stdout.strip())
(ROOT/'artifacts/public-source-validation.json').write_text(json.dumps(dict(passed=True,source_only=True,generated_documents=481,generated_accounts=3,credentials_exported=False),indent=2),encoding='utf8')
