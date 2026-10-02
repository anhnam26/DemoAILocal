"""Build a source-only Linux release using a positive allowlist (no secrets/data)."""
import argparse
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FILES=('main.py','start.sh','requirements.txt','requirements-lock.txt','.env.example',
       'README.md','SECURITY.md','deploy/cyberant.service.example','deploy/nginx.conf.example',
       'docs/DEPLOYMENT.md','docs/DATA_LAYOUT.md','docs/PUBLIC_SHARE.md',
       'docs/SERVICE_RAG.md','tools/audit_service_sources.py')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    output=Path(args.output).resolve()
    if output.exists():raise ValueError('Refusing to overwrite release')
    files=[ROOT/name for name in FILES]
    files+=list((ROOT/'cyberant').rglob('*.py'))
    files+=list((ROOT/'knowledge').rglob('*.json'))
    files+=list((ROOT/'static').glob('*'))
    if any(not p.is_file() or p.is_symlink() for p in files):raise ValueError('Missing/unsafe release file')
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            archive.write(path,path.relative_to(ROOT).as_posix())
    print(f'Release: {output} ({len(set(files))} files; no .env, DB, logs, test artifacts or Windows environment)')


if __name__=='__main__':main()