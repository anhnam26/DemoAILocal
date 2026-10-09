"""Build an allowlisted release; secrets/data require explicit private mode."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FILES=('main.py','start.sh','requirements.txt','requirements-lock.txt','.env.example',
       'README.md','SECURITY.md','deploy/cyberant.service.example','deploy/nginx.conf.example',
       'docs/DEPLOYMENT.md','docs/DATA_LAYOUT.md','docs/PUBLIC_SHARE.md',
         'docs/SERVICE_RAG.md','docs/CONVERSATION_WEB.md','docs/KNOWLEDGE_ACCEPTANCE.md','docs/CONFIGURATION_GUIDES.md','docs/PRIVATE_BUNDLE.md')
MODULES=('__init__','accounts','admin_system','app','config','conversations','generation',
         'http_limits','legacy','model_provider','operations','provider_errors','quality_feedback',
          'public_share','rag','runtime_lock','service_evidence','storage','sync_knowledge','token_usage','web_search','attachments','document_extractors','url_reader')
ASSETS=('index.html','Logo.png','answer-renderer.js','app.js','conversations.js','feedback.js',
        'login-aurora.js','management.js','theme.js','conversation-web.css','management.css',
        'modern.css','quality.css','readability.css','style.css','workspace.css')


def release_files(root=ROOT):
    root=Path(root).resolve()
    def safe(relative):
        relative=Path(relative)
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('Unsafe release path')
        path=root/relative
        if any((root/Path(*relative.parts[:i])).is_symlink() for i in range(1,len(relative.parts)+1)):
            raise ValueError('Symlink in release path: '+relative.as_posix())
        if not path.resolve().is_relative_to(root) or not path.is_file():raise ValueError('Missing/unsafe release file: '+relative.as_posix())
        return path
    files=[safe(name) for name in FILES]
    files += [safe('cyberant/'+name+'.py') for name in MODULES]
    files += [safe('static/'+name) for name in ASSETS]
    manifest_path=safe('knowledge/manifest.json')
    manifest=json.loads(manifest_path.read_text(encoding='utf8'))
    if manifest.get('version')!=1 or not isinstance(manifest.get('documents'),list) or not manifest['documents']:
        raise ValueError('Invalid corpus manifest')
    seen=set();ids=set()
    for entry in manifest['documents']:
        relative=Path(entry['path'])
        if not relative.parts or relative.parts[0]!='documents' or relative.suffix!='.json':raise ValueError('Invalid corpus path')
        path=safe(Path('knowledge')/relative)
        if path in seen or entry['id'] in ids:raise ValueError('Duplicate corpus entry')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Corpus checksum mismatch')
        if json.loads(raw)['id']!=entry['id']:raise ValueError('Corpus ID mismatch')
        seen.add(path);ids.add(entry['id']);files.append(path)
    actual=set((root/'knowledge/documents').rglob('*.json'))
    if seen!=actual:raise ValueError('Manifest does not cover corpus')
    return sorted(set(files+[manifest_path]))


def package(output,root=ROOT):
    root=Path(root).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('Refusing to overwrite release')
    files=release_files(root)
    output.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation prevents accidental concurrent overwrite.
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as archive:
        for path in files:archive.write(path,path.relative_to(root).as_posix())
    return len(files)


def portable_env(text):
    """Keep every original setting except the two machine-dependent data paths."""
    replacements={'APP_DATA_DIR':'data','APP_BACKUP_DIR':'../CyberAnt-private/backups'}
    lines=[];seen=set()
    for line in text.splitlines():
        key=line.strip().removeprefix('export ').split('=',1)[0].strip()
        if key in replacements and '=' in line:
            lines.append(key+'='+replacements[key]);seen.add(key)
        else:lines.append(line)
    lines.extend(key+'='+value for key,value in replacements.items() if key not in seen)
    return '\n'.join(lines)+'\n'


def package_private(output,runtime,env_file,root=ROOT):
    """Offline consistent snapshot, no session reuse, never modify source runtime/config."""
    sys.path.insert(0,str(ROOT))
    from cyberant import operations,runtime_lock,storage
    root=Path(root).resolve();output=Path(output).resolve()
    runtime=Path(runtime).resolve();env_file=Path(env_file).resolve()
    if output.exists():raise ValueError('Refusing to overwrite release')
    if output.is_relative_to(root) or output.is_relative_to(runtime):
        raise ValueError('Private release must be outside source/runtime')
    files=release_files(root)
    if not env_file.is_file():raise ValueError('Explicit environment file is missing')
    text=env_file.read_text(encoding='utf-8-sig')
    output.parent.mkdir(parents=True,exist_ok=True)
    lock=runtime_lock.acquire(runtime)
    try:
        with storage.connect(runtime) as c:
            if c.execute("SELECT COUNT(*) FROM token_usage WHERE status IN ('reserved','sent')").fetchone()[0]:
                raise ValueError('Runtime has active reservations; wait for completion or reconcile before packaging')
        with tempfile.TemporaryDirectory(prefix='.cyberant-private-',dir=output.parent) as temp:
            temp=Path(temp)
            operations.backup(runtime,temp/'snapshot')
            operations.restore(temp/'snapshot',temp/'data')
            with storage.connect(runtime) as before,storage.connect(temp/'data') as after:
                for group in storage.STORES.values():
                    for table in group:
                        if table!='sessions' and storage.digest_table(before,table)!=storage.digest_table(after,table):
                            raise ValueError('Snapshot table mismatch: '+table)
                if after.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]:
                    raise ValueError('Copied sessions must be revoked')
            env=temp/'.env';env.write_text(portable_env(text),encoding='utf8',newline='\n')
            private={'.env':env,'data/layout.json':temp/'data/layout.json'}
            private.update({'data/'+p.relative_to(temp/'data').as_posix():p for p in storage.paths(temp/'data').values()})
            try:
                # Set owner-only file mode in ZIP metadata as well as the archive itself.
                with output.open('xb') as stream:
                    os.chmod(output,0o600)
                    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
                        for path in files:archive.write(path,path.relative_to(root).as_posix())
                        for name,path in private.items():
                            info=zipfile.ZipInfo.from_file(path,name);info.create_system=3
                            info.external_attr=0o100600<<16
                            archive.writestr(info,path.read_bytes(),compress_type=zipfile.ZIP_DEFLATED)
            except Exception:
                # Only remove an incomplete archive created by this invocation.
                if 'stream' in locals():output.unlink(missing_ok=True)
                raise
    finally:lock.close()
    return len(files)+len(private)


def main():
    if os.name=='posix':os.umask(0o077)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    parser.add_argument('--list',action='store_true',help='Inspect allowlisted paths without creating an archive')
    parser.add_argument('--private-runtime',help='Explicit offline runtime to snapshot; ZIP will contain private data')
    parser.add_argument('--env-file',help='Explicit config with secrets, required with --private-runtime')
    args=parser.parse_args()
    private=bool(args.private_runtime or args.env_file)
    if private and (not args.private_runtime or not args.env_file or not args.output):
        parser.error('Private mode requires --output, --private-runtime and --env-file')
    if args.list:
        for path in release_files():print(path.relative_to(ROOT).as_posix())
    if args.output:
        count=package_private(args.output,args.private_runtime,args.env_file) if private else package(args.output)
        label='PRIVATE: contains API keys and databases; ZIP is NOT encrypted, do not publish' if private else 'source-only: no .env or runtime databases'
        print(f'Release: {Path(args.output).resolve()} ({count} files; {label})')
    elif not args.list:parser.error('Specify --output or --list')


if __name__=='__main__':main()