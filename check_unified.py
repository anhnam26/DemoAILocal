"""Live UI and API smoke test. One small real completion when --live is supplied."""
import json,sys,time
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent
seeds=json.loads((ROOT/'data/initial-accounts.json').read_text(encoding='utf8'))['accounts']
admin=next(a for a in seeds if a['role']=='admin')
report={};errors=[]
with httpx.Client(base_url='http://127.0.0.1:8088',timeout=180,trust_env=False) as c:
    report['health']=c.get('/api/health').json()
    response=c.post('/api/login',json={k:admin[k] for k in ('username','password')})
    response.raise_for_status()
    report['documents']=len(c.get('/api/documents').json())
    report['old_routes']={p:c.get(p).status_code for p in ('/internal/','/demo','/api/finance','/api/operations')}
    if '--live' in sys.argv:
        cv=c.post('/api/conversations').json()['id']
        try:
            r=c.post('/api/chat',json={'question':'RMA là gì? Trả lời ngắn và dẫn nguồn.','conversation_id':cv})
            report['live_status']=r.status_code;report['live']=r.json()
            (ROOT/'artifacts/live_api.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
        finally:c.delete('/api/conversations/'+cv)
    c.post('/api/logout')
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,channel='msedge')
    page=browser.new_page(viewport={'width':1440,'height':1000})
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:8088')
    page.locator('#login-username').fill(admin['username']);page.locator('#login-password').fill(admin['password'])
    page.locator('#login-submit').click();page.locator('#workspace').wait_for(state='visible')
    for view in ('knowledge','users','system','admin','history','chat'):
        page.locator(f'nav button[data-view="{view}"]').click();page.wait_for_timeout(500)
    assert page.locator('nav button[data-view="finance"]').count()==0
    assert page.locator('#user-role-select option').all_text_contents()==['Thành viên','Quản trị']
    page.screenshot(path=str(ROOT/'artifacts/unified-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(200)
    if page.locator('#sidebar-toggle').get_attribute('aria-expanded')=='true':page.locator('#sidebar-toggle').click()
    page.screenshot(path=str(ROOT/'artifacts/unified-mobile.png'),full_page=True)
    report['browser_errors']=errors;report['browser_ok']=not errors
    if page.locator('#sidebar-toggle').get_attribute('aria-expanded')=='false':page.locator('#sidebar-toggle').click()
    page.locator('#logout').click();browser.close()
(ROOT/'artifacts/unified_smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))
if errors:raise SystemExit(1)
