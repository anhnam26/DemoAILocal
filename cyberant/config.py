"""Environment configuration shared by the API and deployment entrypoint."""
import os
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]

def env():
    values={}
    path=env_path()
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
    values=env();mode=values.get('APP_ENV','development')
    if mode not in ('development','lan','production'):raise ValueError('APP_ENV must be development, lan or production')
    production=mode=='production'
    origins=[x.strip().rstrip('/') for x in values.get('APP_ORIGINS','http://localhost:8088,http://127.0.0.1:8088,http://testserver').split(',') if x.strip()]
    if not origins:raise ValueError('APP_ORIGINS must not be empty')
    for origin in origins:
        parsed=urlsplit(origin)
        if (parsed.scheme not in ('http','https') or not parsed.hostname or parsed.path or
                parsed.query or parsed.fragment or parsed.username is not None or parsed.password is not None or
                '*' in parsed.netloc or any(c.isspace() for c in origin)):
            raise ValueError('APP_ORIGINS must contain exact http(s) origins without paths, credentials or wildcards')
        if parsed.port is not None and not 1<=parsed.port<=65535:raise ValueError('Invalid APP_ORIGINS port')
        if mode=='lan':
            import ipaddress
            try:ip=ipaddress.ip_address(parsed.hostname)
            except ValueError:
                if parsed.hostname!='localhost':raise ValueError('LAN origins must use a private IP address or localhost')
            else:
                networks=('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','127.0.0.0/8','fc00::/7','::1/128')
                if not any(ip in ipaddress.ip_network(n) for n in networks):raise ValueError('LAN origin must be a private or loopback address')
    if production and any(not x.startswith('https://') for x in origins):raise ValueError('Production requires HTTPS APP_ORIGINS')
    hosts={urlsplit(x).hostname for x in origins}|{'localhost','127.0.0.1'}
    return dict(production=production,server=mode!='development',mode=mode,origins=origins,hosts=hosts,secure_cookie=production)

def env_path():
    path=Path(os.environ.get('APP_ENV_FILE',str(ROOT/'.env'))).expanduser()
    if not path.is_absolute():path=ROOT/path
    if 'APP_ENV_FILE' in os.environ and not path.is_file():raise ValueError('APP_ENV_FILE does not exist')
    return path

def data_dir():
    path=Path(env().get('APP_DATA_DIR',str(ROOT/'data'))).expanduser()
    return (path if path.is_absolute() else ROOT/path).resolve()

def backup_dir():
    path=Path(env().get('APP_BACKUP_DIR',str(data_dir()/'backups'))).expanduser()
    return (path if path.is_absolute() else ROOT/path).resolve()
