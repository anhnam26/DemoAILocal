"""Build a source-only GitHub bundle, excluding runtime data and git history.
Does not publish anything. Checks current local credential values without printing them.
"""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).parent
FILES=['app.py','accounts.py','admin_system.py','system_runtime.py','runtime_limits.py','generation.py','conversations.py','business.py','finance_logic.py','seed_data.py','company_data.py','security_data.py','finance_data.py','workflow_data.py','download_model.py','Backup-Data.py','Start-Demo.ps1','Stop-Demo.ps1','Restart-App.ps1','requirements-lock.txt','testing_accounts.py','export_public.py','benchmark_context.py','README.md','SECURITY.md','CONTRIBUTING.md','LUONG_HOAT_DONG.txt','.gitignore','.gitattributes']

def build():
    paths=[ROOT/x for x in FILES]
    paths+=list((ROOT/'static').glob('*.js'))+list((ROOT/'static').glob('*.css'))+list((ROOT/'static').glob('*.html'))
    paths+=list((ROOT/'docs').glob('*.md'))+list((ROOT/'examples').glob('*.json'))+list(ROOT.glob('test_*.py'))
    paths+=list(ROOT.glob('check_*ui.py'))+[ROOT/'check_readability.py',ROOT/'check_concurrent_chat.py',ROOT/'check_four_slots.py']
    secrets=[]
    key=ROOT/'data/model-api-key.txt'
    if key.exists():secrets.append(key.read_text(encoding='utf8').strip())
    account=ROOT/'data/initial-accounts.json'
    if account.exists():secrets.extend(x['password'] for x in json.loads(account.read_text(encoding='utf8'))['accounts'])
    # History is deliberately never exported; only report metadata, no secret values.
    missing=[p.name for p in paths if not p.is_file()]
    if missing:raise RuntimeError('Missing public files: '+', '.join(missing))
    members={}
    for p in sorted(set(paths)):
        raw=p.read_bytes();name=p.relative_to(ROOT).as_posix()
        if any(secret and secret.encode() in raw for secret in secrets):raise RuntimeError('Known credential found in '+name)
        members[name]=raw
    out=ROOT/'exports';out.mkdir(exist_ok=True)
    target=out/'cyberant-ai-source.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for name,raw in members.items():z.writestr('cyberant-ai/'+name,raw)
    report=dict(files=len(members),bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),known_secret_scan='passed',excluded=['data/','models/','runtime/','.git/','logs/','backups/','artifacts/','virtual environments'],note='Allowlisted source only. No remote publish. Known-secret scanning is not a general certification.')
    (out/'public-export-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False));return target
if __name__=='__main__':build()
