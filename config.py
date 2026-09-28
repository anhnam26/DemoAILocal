"""Environment configuration shared by the API and deployment entrypoint."""
import os
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parent

def env():
    values={}
    path=ROOT/'.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line=line.strip()
            if line and not line.startswith('#') and '=' in line:
                key,value=line.removeprefix('export ').split('=',1)
                values[key.strip()]=value.strip().strip('\"\'')
    values.update(os.environ)
    return values

def integer(name,default,low,high):
    value=int(env().get(name,default))
    if not low<=value<=high:raise ValueError(f'{name} must be between {low} and {high}')
    return value

def security():
    values=env();production=values.get('APP_ENV','development')=='production'
    origins=[x.strip().rstrip('/') for x in values.get('APP_ORIGINS','http://localhost:8088,http://127.0.0.1:8088,http://testserver').split(',') if x.strip()]
    if not origins or any(urlsplit(x).scheme not in ('http','https') or not urlsplit(x).hostname or urlsplit(x).path for x in origins):
        raise ValueError('APP_ORIGINS must contain exact http(s) origins without paths')
    if production and any(not x.startswith('https://') for x in origins):raise ValueError('Production requires HTTPS APP_ORIGINS')
    hosts={urlsplit(x).hostname for x in origins}|{'localhost','127.0.0.1'}
    return dict(production=production,origins=origins,hosts=hosts,secure_cookie=production)

def data_dir():return Path(env().get('APP_DATA_DIR',str(ROOT/'data'))).resolve()
