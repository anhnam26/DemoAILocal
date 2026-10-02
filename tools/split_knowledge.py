"""One-time lossless split of legacy corpus; never deletes the input file."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True)
    parser.add_argument('--target',required=True)
    args=parser.parse_args()
    source=Path(args.source)
    target=Path(args.target)
    if (target/'manifest.json').exists() or (target/'documents').exists():raise ValueError('Target corpus already exists')
    docs=json.loads(source.read_text(encoding='utf8'))
    ids=set();entries=[]
    for d in docs:
        id=d['id'];group=d['group']
        if id in ids or not id or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-' for c in id) or group not in 'ABCDEF':raise ValueError('Invalid/duplicate ID or group')
        ids.add(id)
    for d in docs:
        relative=f"documents/{d['group']}/{d['id']}.json"
        path=target/relative
        path.parent.mkdir(parents=True,exist_ok=True)
        raw=(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf8')
        path.write_bytes(raw)
        entries.append({'id':d['id'],'path':relative,'sha256':hashlib.sha256(raw).hexdigest()})
    manifest={'version':1,'documents':entries}
    (target/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    rebuilt=[json.loads((target/e['path']).read_bytes()) for e in entries]
    if rebuilt!=docs:raise ValueError('Lossless comparison failed')
    print(f'Lossless split verified: {len(docs)} documents')


if __name__=='__main__':main()