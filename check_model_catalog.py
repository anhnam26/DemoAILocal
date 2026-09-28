import json
from pathlib import Path
import httpx,model_provider
s=model_provider.settings()
r=httpx.get('https://openrouter.ai/api/v1/models',timeout=30,trust_env=False)
r.raise_for_status();models=r.json()['data'];ids={m['id'] for m in models}
requested=s['model'];native=requested.removeprefix('openrouter/') if requested.count('/')>1 else requested
print(json.dumps({'requested':requested,'exists':requested in ids,'native':native,'native_exists':native in ids,
                  'matching':[m['id'] for m in models if 'nemotron-3-super' in m['id']]},indent=2))
if requested not in ids and native in ids:
    path=Path('.env');lines=path.read_text(encoding='utf8').splitlines()
    for i,line in enumerate(lines):
        if '=' in line and line.split('=',1)[0].strip() in ('MODEL','OPENROUTER_MODEL'):
            lines[i]=line.split('=',1)[0]+'='+native
    path.write_text('\n'.join(lines)+'\n',encoding='utf8')
    print('Corrected model identifier in .env; API key unchanged.')
