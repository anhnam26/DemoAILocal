from testing_accounts import credentials,browser_login
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
import json,httpx
root=Path(__file__).parent;out=root/'artifacts';errors=[];report=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000})
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8088',wait_until='networkidle')
    browser_login(page,'sale');page.locator('.suggestion').first.wait_for()
    def ask(q,expected):
        previous=page.locator('.message.assistant').count()
        page.locator('#question').fill(q);page.locator('#send').click()
        expect(page.locator('.message.assistant')).to_have_count(previous+1,timeout=60000)
        expect(page.locator('.message.assistant').last).to_contain_text(expected)
        report.append({'question':q,'expected':expected,'passed':True})
    ask('Firewall mạng và WAF khác nhau như thế nào?','WAF')
    ask('Tạo bảng đề ra các mục so sánh giữa 2 cái đó','Tiêu chí')
    assert page.locator('.message.assistant').last.locator('table').count()==1
    page.screenshot(path=str(out/'06-company-comparison.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(out/'07-company-mobile.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1000})
    ask('Triển khai firewall bao lâu và mất bao nhiêu tiền?','12.000.000')
    ask('So sánh BASIC PLUS PREMIUM về giá SLA và bảo trì','30 phút')
    ask('Hợp đồng bảo trì của An Minh Retail có những gì?','CONTRACT-A')
    page.locator('[data-view="operations"]').click();page.locator('.operation-card').first.wait_for()
    expect(page.locator('#operation-stats')).to_contain_text('Khách hàng')
    page.locator('#operation-kind').select_option('Dự án');expect(page.locator('.operation-card')).to_have_count(10)
    page.screenshot(path=str(out/'08-company-projects.png'),full_page=True)
    page.locator('#operation-search').fill('An Minh');expect(page.locator('.operation-card')).to_have_count(2)
    page.locator('.operation-card [data-doc]').first.click();expect(page.locator('#modal-body')).to_contain_text('Dự án DEMO');page.locator('#close-modal').click()
    page.locator('.operation-card [data-question]').first.click();expect(page.locator('.message.assistant').last).to_contain_text('PROJECT-A-01',timeout=10000)
    page.locator('#new-chat').click();expect(page.locator('.message.assistant')).to_have_count(0)
    page.reload(wait_until='networkidle');expect(page.locator('.message.assistant')).to_have_count(0)
    assert '<img' not in page.evaluate('renderAnswer("<img src=x onerror=alert(1)>")')
    page.locator('#logout').click();browser_login(page,'technical');page.locator('.suggestion').first.wait_for()
    ask('Tóm tắt TICKET-B-02','Retention')
    page.locator('[data-view="operations"]').click();page.locator('.operation-card').first.wait_for()
    page.locator('#operation-kind').select_option('Ticket');page.locator('#operation-search').fill('');expect(page.locator('.operation-card')).to_have_count(20)
    page.screenshot(path=str(out/'09-company-tickets.png'),full_page=True);browser.close()
assert not errors,errors
with httpx.Client(base_url='http://127.0.0.1:8088',trust_env=False) as c:
    c.post('/api/login',json=credentials('admin')).raise_for_status()
    ops=c.get('/api/operations').json();assert sum(ops['counts'][k] for k in ('Kho hàng','Khách hàng','Hợp đồng','Dự án','Báo giá','Nhân sự','Ticket'))==134
    health=c.get('/api/health').json();assert health['ready']
(out/'company-ui-report.json').write_text(json.dumps(dict(passed=True,checks=report,console_errors=errors,admin_counts=ops['counts'],health=health),ensure_ascii=False,indent=2),encoding='utf8')
print('Company demo: 6 chat scenarios, follow-up table, mobile, operations search, source navigation, reset, ACL counts and GPU readiness passed.')
