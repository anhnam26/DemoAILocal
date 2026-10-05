"""Explicit, audited acceptance of draft knowledge; default is read-only dry-run."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
from datetime import datetime,timezone
from contextlib import closing

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cyberant import config,operations,runtime_lock,storage,sync_knowledge


def encode(value):return json.dumps(value,ensure_ascii=False,sort_keys=True)


def inventory(manifest,runtime):
    documents=sync_knowledge.load(manifest)
    db=storage.paths(runtime)['knowledge']
    with closing(sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)) as c:
        rows={id:json.loads(raw) for id,raw in c.execute('SELECT id,payload FROM docs')}
        digests=dict(c.execute('SELECT id,digest FROM source_sync'))
    for d in documents:
        old=rows.get(d['id'])
        # Only the existing administrative retirement override is compatible.
        if old is None or {**old,'status':d['status']}!=d:
            raise ValueError('Runtime/source divergence; review before acceptance: '+d['id'])
        if digests.get(d['id'])!=hashlib.sha256(encode(d).encode()).hexdigest():
            raise ValueError('Source sync digest mismatch: '+d['id'])
    return documents,rows


def accepted(d,stamp,reason):
    if d.get('review_status')!='draft_engineer_review':return d
    updated={**d,'review_status':'accepted',
             'review_decision':dict(previous_status='draft_engineer_review',accepted_at=stamp,
                                    authority='user_request',reason=reason,
                                    scope='knowledge_use_not_deployment_verification')}
    if isinstance(d.get('provenance'),dict) and d['provenance'].get('review_status')=='draft_engineer_review':
        updated['provenance']={**d['provenance'],'review_status':'accepted'}
    return updated


def run(manifest,runtime,backup=None,reason=None):
    manifest=Path(manifest).resolve();runtime=Path(runtime).resolve()
    documents,rows=inventory(manifest,runtime)
    ids=sorted(id for id,d in rows.items() if d.get('review_status')=='draft_engineer_review')
    source_ids=sorted(d['id'] for d in documents if d.get('review_status')=='draft_engineer_review')
    result=dict(source_drafts=len(source_ids),runtime_drafts=len(ids),runtime_only_drafts=len(set(ids)-set(source_ids)))
    if backup is None or not ids:return {**result,'applied':False}
    if not reason or not reason.strip():raise ValueError('Acceptance requires an explicit reason')
    target=Path(backup).resolve()
    if target.exists():raise ValueError('Backup destination must not exist')
    if target.is_relative_to(manifest.parent) or target.is_relative_to(runtime):raise ValueError('Backup must be outside corpus/runtime')
    lock=runtime_lock.acquire(runtime)
    try:
        documents,rows=inventory(manifest,runtime)
        target.mkdir(parents=True,mode=0o700)
        operations.backup(runtime,target/'runtime')
        operations.restore(target/'runtime',target/'restore-check')
        # Restore revokes sessions by design; every other table must be identical.
        with storage.connect(runtime) as before,storage.connect(target/'restore-check') as after:
            for tables in storage.STORES.values():
                for table in tables:
                    if table!='sessions' and storage.digest_table(before,table)!=storage.digest_table(after,table):
                        raise ValueError('Backup restore differs: '+table)
        shutil.copytree(manifest.parent,target/'knowledge')
        stamp=datetime.now(timezone.utc).isoformat()
        receipt={**result,'accepted_at':stamp,'reason':reason,'source_ids':source_ids,'runtime_ids':ids}
        operations._write_json(target/'acceptance.json',receipt)
        new_docs=[accepted(d,stamp,reason) for d in documents]
        entries=json.loads(manifest.read_text(encoding='utf8'))
        by_id={d['id']:d for d in new_docs}
        try:
            with storage.connect(runtime) as c:
                c.execute('BEGIN IMMEDIATE')
                # Recheck under transaction; never overwrite concurrent payload changes.
                actual={id:json.loads(raw) for id,raw in c.execute('SELECT id,payload FROM docs')}
                if actual!=rows:raise ValueError('Runtime changed during backup; no acceptance applied')
                for id in ids:
                    c.execute('UPDATE docs SET payload=? WHERE id=?',(encode(accepted(rows[id],stamp,reason)),id))
                for entry in entries['documents']:
                    if entry['id'] not in source_ids:continue
                    d=by_id[entry['id']];path=manifest.parent/entry['path']
                    operations._write_json(path,d)
                    entry['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
                    c.execute('UPDATE source_sync SET digest=? WHERE id=?',(hashlib.sha256(encode(d).encode()).hexdigest(),d['id']))
                operations._write_json(manifest,entries)
                sync_knowledge.load(manifest)
                c.execute('INSERT INTO audit(ts,action,role,detail) VALUES(?,?,?,?)',
                          (stamp,'knowledge_acceptance','admin',encode(receipt)))
        except Exception:
            # Database context rolls back; restore only files touched by this task.
            for entry in entries['documents']:
                if entry['id'] in source_ids:shutil.copyfile(target/'knowledge'/entry['path'],manifest.parent/entry['path'])
            shutil.copyfile(target/'knowledge'/manifest.name,manifest)
            raise
        inventory(manifest,runtime)
        return {**result,'applied':True,'backup':str(target),'remaining_drafts':0}
    finally:lock.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',default=str(ROOT/'knowledge/manifest.json'))
    parser.add_argument('--runtime',default=str(config.data_dir()))
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--backup-dir')
    parser.add_argument('--reason')
    args=parser.parse_args()
    if args.apply and (not args.backup_dir or not args.reason):parser.error('--apply requires --backup-dir and --reason')
    print(json.dumps(run(args.manifest,args.runtime,args.backup_dir if args.apply else None,args.reason),ensure_ascii=False,indent=2))


if __name__=='__main__':main()