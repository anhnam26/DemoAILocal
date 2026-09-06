from pathlib import Path
import json
from playwright.sync_api import sync_playwright,expect
from testing_accounts import browser_login
root=Path(__file__).parent;errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8088');browser_login(page,'admin')
    page.locator('[data-view="system"]').click();expect(page.locator('#runtime-parallel option')).to_have_count(4)
    page.locator('#runtime-parallel').select_option('4');page.locator('#runtime-context').fill('8192');page.locator('#runtime-tokens').fill('8192')
    expect(page.locator('#budget-preview tbody tr')).to_have_count(4);expect(page.locator('#budget-preview')).to_contain_text('2.048');expect(page.locator('#budget-preview')).to_contain_text('32.768')
    expect(page.locator('#running-budgets tbody tr')).to_have_count(2)
    page.wait_for_timeout(6100)
    expect(page.locator('#runtime-parallel')).to_have_value('4');expect(page.locator('#budget-preview tbody tr')).to_have_count(4)
    page.screenshot(path=str(root/'artifacts/26-token-budgets.png'),full_page=True)
    for width in (390,768,1440):
        page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
    # Do not save the preview; test deleting only a conversation created by this test.
    page.locator('[data-view="history"]').click();page.locator('#history-new').click()
    page.locator('#question').fill('Firewall và WAF khác nhau như thế nào?');page.locator('#send').click();expect(page.locator('.message.assistant')).to_have_count(1,timeout=20000)
    id=page.evaluate('currentConversation');page.locator('[data-view="history"]').click();button=page.locator('[data-delete-conversation="'+id+'"]')
    page.once('dialog',lambda d:d.dismiss());button.click();expect(button).to_be_visible()
    page.screenshot(path=str(root/'artifacts/27-delete-conversation.png'),full_page=True)
    page.once('dialog',lambda d:d.accept());button.click();expect(button).to_have_count(0)
    page.reload();expect(page.locator('#workspace')).to_be_visible();page.locator('[data-view="history"]').click();expect(page.locator('[data-delete-conversation="'+id+'"]').first).to_have_count(0)
    assert page.evaluate('async id=>(await fetch("/api/conversations/"+id)).status',id)==404
    page.locator('#logout').click();browser.close()
assert not errors,errors
(root/'artifacts/admin-budgets-ui-report.json').write_text(json.dumps(dict(passed=True,errors=errors,checks=['1-4 slots preview','per-slot output clamp','saved vs running','responsive','delete cancel','delete confirm','no resurrection after reload']),indent=2),encoding='utf8')
print('Token budget preview and conversation deletion UI passed.')
