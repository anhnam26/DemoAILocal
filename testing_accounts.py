"""Local QA helper: reads initial passwords without embedding credentials in tests or reports."""
from pathlib import Path
import json
def credentials(role):
    items=json.loads((Path(__file__).parent/'data'/'initial-accounts.json').read_text(encoding='utf8'))['accounts']
    item=next(x for x in items if x['role']==role)
    return dict(username=item['username'],password=item['password'])
def browser_login(page,role):
    c=credentials(role);page.locator('#login-username').fill(c['username']);page.locator('#login-password').fill(c['password']);page.locator('#login-submit').click();page.locator('#workspace').wait_for(state='visible')
