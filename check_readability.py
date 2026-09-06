from testing_accounts import credentials,browser_login
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
import json
root=Path(__file__).parent;out=root/'artifacts';errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    context=browser.new_context(viewport={'width':1440,'height':1000},permissions=['clipboard-read','clipboard-write'])
    page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8088',wait_until='networkidle');browser_login(page,'technical');page.locator('#new-chat').click();page.locator('#workspace').wait_for(state='visible')
    page.screenshot(path=str(out/'10-readable-home.png'),full_page=True)
    page.locator('#question').fill('Checklist ứng cứu khi nghi nhiễm ransomware gồm những gì?');page.locator('#send').click()
    page.locator('.message.assistant').wait_for(timeout=180000)
    answer=page.locator('.message.assistant').last
    assert answer.locator('.answer-heading').count()>=2,answer.inner_text()
    assert answer.locator('li').count()>=3,answer.inner_text()
    assert 'Qwen3.5-9B + RAG' in answer.inner_text()
    assert page.locator('.message-text').evaluate('(el)=>getComputedStyle(el).fontSize')=='18px'
    page.locator('#font-larger').click();expect(page.locator('#reading-size')).to_have_text('20px')
    page.reload(wait_until='networkidle');expect(page.locator('#reading-size')).to_have_text('20px')
    page.locator('#workspace').wait_for(state='visible');answer=page.locator('.message.assistant').last
    answer.locator('[data-copy-answer]').click()
    copied=page.evaluate('navigator.clipboard.readText()');assert 'ransomware' in copied.lower()
    with page.expect_download() as dl:answer.locator('[data-save-answer]').click()
    dl.value.save_as(str(out/'readability-answer.md'))
    assert (out/'readability-answer.md').read_text(encoding='utf8')==copied.replace('\r\n','\n')
    answer.locator('[data-collapse-answer]').click();expect(answer.locator('.message-text')).to_be_hidden()
    answer.locator('[data-collapse-answer]').click();expect(answer.locator('.message-text')).to_be_visible()
    page.locator('.chat-main').evaluate('(el)=>el.scrollTop=0')
    page.screenshot(path=str(out/'11-readable-answer.png'),full_page=True)
    for width in [390,768,1440]:
        page.set_viewport_size({'width':width,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
    page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'12-readable-mobile.png'),full_page=True)
    page.set_viewport_size({'width':1440,'height':1000});page.locator('[data-view="knowledge"]').click()
    page.locator('#doc-category').select_option('Bảo mật AI');expect(page.locator('.doc-card')).to_have_count(2)
    page.locator('[data-doc="SEC-GUIDE-AI-RAG"]').click()
    expect(page.locator('#modal-body h3')).to_have_count(5)
    assert page.locator('#modal-references a').get_attribute('href').startswith('https://cheatsheetseries.owasp.org/')
    page.screenshot(path=str(out/'13-security-source.png'),full_page=True)
    # Raw HTML, headings, lists, code and table all stay text-safe.
    rendered=page.evaluate('renderAnswer("## Mục\\n- Một ý\\n- <img src=x onerror=alert(1)>\\n\\n```\\n<script>alert(1)</script>\\n```\\n| A | B |\\n| --- | --- |\\n| 1 | 2 |")')
    assert '<img' not in rendered and '<script>' not in rendered and '<li>' in rendered and '<table' in rendered
    browser.close()
assert not errors,errors
(out/'readability-report.json').write_text(json.dumps(dict(passed=True,default_font=18,persisted_font=20,security_model_answer=copied,errors=errors,checks=['real GPU structured answer','font controls persistence','clipboard','Markdown download','collapse','390/768/1440 no overflow','knowledge category','source reference links','safe Markdown']),ensure_ascii=False,indent=2),encoding='utf8')
print('Readability and security GPU scenario passed; evidence in artifacts/readability-report.json')
