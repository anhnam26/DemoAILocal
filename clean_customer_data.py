"""Sanitize customer examples in NewData workbooks; never delete source theory."""
import json,re
from pathlib import Path
from openpyxl import load_workbook
root=Path(__file__).resolve().parent
processed=root/'NewData/data/processed'
examples=json.loads((processed/'example_customers.json').read_text(encoding='utf8'))
identifiers={str(r[k]) for r in examples for k in ('customer_id','name','contact','email','phone','tax_id') if r.get(k)}
removed=[];redacted=0
for path in (root/'NewData/data/workbooks').glob('*.xlsx'):
    wb=load_workbook(path);changed=False
    for sheet in list(wb):
        if sheet.title.lower().startswith('example_') or sheet.title=='Du_lieu_MINH_HOA':
            removed.append(path.name+':'+sheet.title);wb.remove(sheet);changed=True;continue
        for row in sheet:
            for cell in row:
                if isinstance(cell.value,str) and any(x in cell.value for x in identifiers):
                    cell.value=None;changed=True;redacted+=1
    if changed:wb.save(path)
    wb.close()
# Existing credentials continue working; role labels and customer assignments disappear.
path=root/'data/initial-accounts.json'
if path.exists():
    data=json.loads(path.read_text(encoding='utf8'))
    for account in data['accounts']:
        account['role']='admin' if account['role']=='admin' else 'member';account['customers']=[]
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
(root/'artifacts/customer_cleanup.json').write_text(json.dumps({'removed_example_sheets':removed,'redacted_cells':redacted},ensure_ascii=False,indent=2),encoding='utf8')
print('Removed example sheets:',len(removed),'Redacted cells:',redacted)
