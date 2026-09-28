from pathlib import Path
import json
for line in Path('.env').read_text(encoding='utf-8-sig').splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        k,v=line.split('=',1);print(k.strip(), '=',v.strip() if 'MODEL' in k.upper() else '<hidden>')
for name in ('static/management.js','sync_knowledge.py','test_app.py','static/conversations.js'):
    print('\nFILE',name);print(Path(name).read_text(encoding='utf8'))
