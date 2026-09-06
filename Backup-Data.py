from pathlib import Path
from datetime import datetime
import sqlite3,shutil
root=Path(__file__).parent
out=root/'backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
out.mkdir(parents=True)
with sqlite3.connect(root/'data'/'demo.sqlite3') as src, sqlite3.connect(out/'demo.sqlite3') as dest:src.backup(dest)
for file in (root/'data').glob('*.json'):
    if file.name != 'initial-accounts.json':shutil.copy2(file,out/file.name)
print(out)
