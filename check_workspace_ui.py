from pathlib import Path
import json,time
from playwright.sync_api import sync_playwright,expect
from testing_accounts import browser_login
root=Path(__file__).parent;out=root/'artifacts';errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8088');browser_login(page,'sale')
    assert page.locator('[data-view="estimate"]').count()==0 and page.locator('#view-estimate').count()==0
    page.locator('[data-view="knowledge"]').click();expect(page.locator('#knowledge-count')).to_contain_text('481')
    page.locator('#doc-search').fill('SEC-LAB-RANSOMWARE');expect(page.locator('#doc-grid .doc-card')).to_have_count(1)
    page.locator('#doc-grid .doc-card').click();expect(page.locator('#document-modal')).to_be_visible();page.locator('#close-modal').click()
    button=page.locator('[data-view="history"]');normal=button.evaluate('(e)=>getComputedStyle(e).backgroundColor');button.hover();page.wait_for_timeout(220)
    assert normal!=button.evaluate('(e)=>getComputedStyle(e).backgroundColor')
    button.click();expect(page.locator('#view-history')).to_be_visible()
    page.locator('#history-new').click();page.locator('#question').fill('Firewall mạng và WAF khác nhau như thế nào?');page.locator('#send').click()
    expect(page.locator('.message.assistant')).to_have_count(1,timeout=30000)
    page.locator('[data-view="history"]').click();expect(page.locator('.conversation-card').first).to_contain_text('Firewall mạng')
    page.screenshot(path=str(out/'22-user-history.png'),full_page=True)
    page.locator('#logout').click();browser_login(page,'sale');expect(page.locator('.message.assistant')).to_have_count(1)
    page.locator('#question').fill('Tạo bảng so sánh hai cái đó');page.locator('#send').click();expect(page.locator('.message.assistant')).to_have_count(2,timeout=30000)
    page.locator('#sidebar-toggle').click();expect(page.locator('#sidebar-toggle')).to_have_attribute('aria-expanded','false')
    page.wait_for_timeout(250);assert page.locator('main').bounding_box()['x']==0
    page.reload();expect(page.locator('#workspace')).to_be_visible();expect(page.locator('#sidebar-toggle')).to_have_attribute('aria-expanded','false')
    for width in (390,768,1440):
        page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
    page.screenshot(path=str(out/'23-sidebar-collapsed.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844});page.locator('#sidebar-toggle').click();expect(page.locator('[data-view="history"]')).to_be_visible();page.locator('[data-view="history"]').click()
    expect(page.locator('#sidebar-toggle')).to_have_attribute('aria-expanded','false');page.screenshot(path=str(out/'24-history-mobile.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1000});page.locator('#sidebar-toggle').click();page.locator('#logout').click();browser_login(page,'admin')
    page.locator('[data-view="system"]').click();expect(page.locator('#runtime-parallel')).to_have_value('2');expect(page.locator('#runtime-context')).to_have_value('4096')
    expect(page.locator('#hardware-metrics')).to_contain_text('RAM toàn máy');page.screenshot(path=str(out/'25-two-slot-system.png'),full_page=True)
    page.locator('[data-view="users"]').click();expect(page.locator('#users-table')).to_contain_text('sales')
    page.locator('#logout').click();browser.close()
assert not errors,errors
(out/'workspace-ui-report.json').write_text(json.dumps(dict(passed=True,errors=errors,checks=['shared lab knowledge','removed service estimation','hover contrast','per-user history','login persistence','continue conversation','sidebar persistence','mobile navigation','responsive 390/768/1440','admin two-slot config']),ensure_ascii=False,indent=2),encoding='utf8')
print('Shared knowledge, history, sidebar, hover and system UI passed.')
