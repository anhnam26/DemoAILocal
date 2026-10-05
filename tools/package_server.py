"""Build a source-only Linux release using a positive allowlist (no secrets/data)."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FILES=('main.py','start.sh','requirements.txt','requirements-lock.txt','.env.example',
       'README.md','SECURITY.md','deploy/cyberant.service.example','deploy/nginx.conf.example',
       'docs/DEPLOYMENT.md','docs/DATA_LAYOUT.md','docs/PUBLIC_SHARE.md',
        'docs/SERVICE_RAG.md','docs/CONVERSATION_WEB.md','docs/KNOWLEDGE_ACCEPTANCE.md','docs/CONFIGURATION_GUIDES.md')
MODULES=('__init__','accounts','admin_system','app','config','conversations','generation',
         'http_limits','legacy','model_provider','operations','public_share','quality_feedback',
         'rag','runtime_lock','service_evidence','storage','sync_knowledge','token_usage','web_search')
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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    parser.add_argument('--list',action='store_true',help='Inspect allowlisted paths without creating an archive')
    args=parser.parse_args()
    if args.list:
        for path in release_files():print(path.relative_to(ROOT).as_posix())
    if args.output:
        count=package(args.output)
        print(f'Release: {Path(args.output).resolve()} ({count} files; no .env, DB, logs, tests, audit fixtures or Windows environment)')
    elif not args.list:parser.error('Specify --output or --list')


if __name__=='__main__':main()