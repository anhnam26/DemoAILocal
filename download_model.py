from pathlib import Path
import urllib.request, json, time, hashlib
root=Path(__file__).parent
dest=root/'models'; dest.mkdir(exist_ok=True)
repo='lmstudio-community/Qwen3.5-9B-GGUF'
filename='Qwen3.5-9B-Q4_K_M.gguf'
meta=json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{repo}?blobs=true'))
entry=next(x for x in meta['siblings'] if x['rfilename']==filename)
target=dest/filename
expected=entry['lfs']['sha256']; size=entry['size']
if not target.exists():
    tmp=target.with_suffix('.partial')
    url=f'https://huggingface.co/{repo}/resolve/{meta["sha"]}/{filename}?download=true'
    with urllib.request.urlopen(url,timeout=90) as source, tmp.open('wb') as out:
        total=0; report=time.monotonic()
        while block:=source.read(4*1024*1024):
            out.write(block); total+=len(block)
            if time.monotonic()-report>20:
                print(f'Download: {total/1e9:.2f}/{size/1e9:.2f} GB',flush=True); report=time.monotonic()
    assert tmp.stat().st_size==size
    tmp.replace(target)
digest=hashlib.file_digest(target.open('rb'),'sha256').hexdigest()
assert digest==expected,'Model checksum mismatch'
(dest/'manifest.json').write_text(json.dumps({'repo':repo,'revision':meta['sha'],'file':filename,'sha256':digest,'bytes':size,'source':'https://lmstudio.ai/models/qwen/qwen3.5-9b'},indent=2))
print('Model verified: '+str(target),flush=True)
