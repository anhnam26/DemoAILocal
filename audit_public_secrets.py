"""Read-only known-secret audit of current tracked files and reachable Git blobs."""
from pathlib import Path
import subprocess,json
R=Path(__file__).parent
known=[(R/'data/model-api-key.txt').read_text().strip().encode()]
known += [a['password'].encode() for a in json.loads((R/'data/initial-accounts.json').read_text())['accounts']]
hits=[]
def git(*args):return subprocess.run(['git',*args],cwd=R,capture_output=True,check=True).stdout
files=git('ls-files','-z').decode().split('\0')
for name in filter(None,files):
    p=R/name
    if p.is_file() and p.stat().st_size<10_000_000 and any(v in p.read_bytes() for v in known):hits.append({'current_file':name})
objects=git('rev-list','--objects','--all').decode().splitlines();checked=0
for line in objects:
    sha=line.split(' ',1)[0]
    kind=git('cat-file','-t',sha).strip()
    if kind!=b'blob':continue
    checked+=1
    raw=git('cat-file','blob',sha)
    if any(v in raw for v in known):hits.append({'history_blob':sha,'path':line.split(' ',1)[-1]})
report=dict(known_secret_hits=hits,current_tracked_files=sum(bool(x) for x in files),historical_blobs_checked=checked,note='Only known current bootstrap passwords and model key; no secret values printed. Export excludes all git history regardless.')
(R/'artifacts/known-secret-audit.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
