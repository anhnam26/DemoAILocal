from pathlib import Path
import json,httpx
from playwright.sync_api import sync_playwright,expect
root=Path(__file__).parent;out=root/'artifacts';errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8088',wait_until='networkidle');page.locator('[data-profile="sale"]').click();page.locator('#workspace').wait_for(state='visible')
    page.locator('[data-view="finance"]').click();expect(page.locator('#finance-calculate')).to_be_enabled()
    expect(page.locator('#finance-offer option')).to_have_count(20);expect(page.locator('#finance-customers tbody tr')).to_have_count(5);expect(page.locator('#finance-pnl')).to_be_hidden()
    page.locator('#finance-offer').select_option('OFFER-FIREWALL');page.locator('#finance-sites').fill('2');page.locator('#finance-discount').fill('5');page.locator('#finance-calculate').click()
    expect(page.locator('#finance-result')).to_contain_text('84.480.000');expect(page.locator('#finance-result')).to_contain_text('328.800.000')
    page.screenshot(path=str(out/'14-finance-dashboard.png'),full_page=True)
    for width in [390,768,1440]:
        page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'15-finance-mobile.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1000});page.locator('#finance-customers [data-question]').first.click()
    expect(page.locator('.message.assistant').last).to_contain_text('AR-A');assert page.locator('.message.assistant').last.locator('table').count()>=1
    page.locator('#question').fill('SLA PLUS chi tiết về khôi phục và bồi hoàn');page.locator('#send').click();expect(page.locator('.message.assistant').last).to_contain_text('130.000')
    page.locator('#logout').click();page.locator('[data-profile="admin"]').click();page.locator('#workspace').wait_for(state='visible')
    page.locator('[data-view="finance"]').click();expect(page.locator('#finance-pnl')).to_be_visible();expect(page.locator('#finance-customers tbody tr')).to_have_count(10)
    page.locator('#finance-pnl').scroll_into_view_if_needed();page.screenshot(path=str(out/'16-finance-admin.png'),full_page=True)
    browser.close()
assert not errors,errors
with httpx.Client(base_url='http://127.0.0.1:8088',trust_env=False,timeout=15) as c:
    c.post('/api/login',json={'profile':'admin'}).raise_for_status();data=c.get('/api/finance').json();assert data['invoice_count']==40
    health=c.get('/api/health').json();assert health['ready']
    documents=c.get('/api/documents').json()
(out/'finance-report.json').write_text(json.dumps(dict(passed=True,document_count=len(documents),totals=data['totals'],aging=data['aging'],pnl=data['pnl'],health=health,errors=errors,checks=['20 offers','2-site discount and tax exact totals','5 vs 10 customer ACL','admin-only P&L','390/768/1440 no overflow','AR chat','SLA credit source']),ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(passed=True,documents=len(documents),totals=data['totals']),ensure_ascii=True))
