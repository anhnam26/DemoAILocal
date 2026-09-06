from pathlib import Path
import json,time,httpx
from playwright.sync_api import sync_playwright,expect
from testing_accounts import credentials,browser_login
root=Path(__file__).parent;out=root/'artifacts';errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1050});page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8088',wait_until='networkidle')
    assert page.locator('.brand-icon').count()==0 and page.locator('[data-profile]').count()==0
    page.screenshot(path=str(out/'17-password-login.png'),full_page=True)
    page.locator('#login-username').fill('sales');page.locator('#login-password').fill('wrong-password');page.locator('#login-submit').click();expect(page.locator('#login-error')).to_contain_text('không đúng')
    browser_login(page,'sale');expect(page.locator('#users-nav')).to_be_hidden();expect(page.locator('#system-nav')).to_be_hidden()
    page.locator('[data-view="estimate"]').click();expect(page.locator('#workflow-template option')).to_have_count(20)
    page.locator('#workflow-template').select_option('mfa');page.locator('#fill-workflow').click()
    expect(page.locator('#workflow-scope')).to_have_value('50 người dùng, 2 ứng dụng SaaS, 1 tenant')
    page.locator('#workflow-notes').fill('Kịch bản kiểm thử giao diện quản trị — dữ liệu DEMO')
    page.locator('#workflow-form .primary').click();card=page.locator('.saved-estimate').first
    expect(card).to_contain_text('10.000.000');expect(card).to_contain_text('Nháp')
    estimate_id=card.locator('small').inner_text().split(' · ')[0]
    card.locator('[data-estimate-transition="submit"]').click();expect(page.locator('.saved-estimate').first).to_contain_text('Chờ duyệt')
    page.screenshot(path=str(out/'18-saved-estimate.png'),full_page=True)
    page.locator('#logout').click();page.locator('#login-submit').wait_for();browser_login(page,'admin')
    page.locator('[data-view="users"]').click();expect(page.locator('#users-table')).to_contain_text('sales');expect(page.locator('#users-table')).to_contain_text('kythuat');expect(page.locator('#sessions-table')).to_contain_text('admin')
    page.screenshot(path=str(out/'19-user-management.png'),full_page=True)
    page.locator('[data-view="estimate"]').click();card=page.locator('.saved-estimate').filter(has_text=estimate_id)
    card.locator('.approval-note').fill('PM xác nhận phạm vi và lịch mẫu; phê duyệt chỉ cho demo')
    card.locator('[data-estimate-transition="approve"]').click();expect(card).to_contain_text('Đã duyệt')
    card.locator('[data-estimate-events]').click();expect(card.locator('.estimate-events')).to_contain_text('approve')
    page.locator('[data-view="system"]').click();expect(page.locator('#hardware-metrics')).to_contain_text('RAM toàn máy',timeout=20000)
    expect(page.locator('#runtime-context')).to_have_value('4096');expect(page.locator('#runtime-observed')).to_contain_text('4096')
    page.locator('#load-system-log').click();expect(page.locator('#system-log')).not_to_have_text('Chọn Đọc log để xem.')
    page.screenshot(path=str(out/'20-live-system.png'),full_page=True)
    for width in [390,768,1440]:
        page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'21-admin-mobile.png'),full_page=True)
    browser.close()
assert not errors,errors
with httpx.Client(base_url='http://127.0.0.1:8088',trust_env=False,timeout=20) as c:
    c.post('/api/login',json=credentials('admin')).raise_for_status();system=c.get('/api/admin/system').json();users=c.get('/api/admin/users').json()
    assert system['ram']['total']>0 and system['gpu']['available'] and system['observed']['context']==4096
(out/'management-report.json').write_text(json.dumps(dict(passed=True,estimate_id=estimate_id,system=system,user_count=len(users['users']),errors=errors,checks=['text branding','password validation','role-restricted navigation','20 complete inputs','save/submit/admin approve/history','online sessions','real CPU RAM VRAM metrics','observed context','system log','390/768/1440 responsive']),ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(passed=True,estimate_id=estimate_id,user_count=len(users['users']),document_count=system['database']['docs']),ensure_ascii=True))
