"""Browser checks through TestClient: no live server or AI charges."""
import json
import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright,expect
import app,model_provider
from test_app import isolated_db,client

@pytest.fixture
def browser_page(monkeypatch):
    monkeypatch.setattr(model_provider,'models',lambda:['test/model','vendor/second'])
    admin=client('admin');member=client().get('/api/me').json()
    payload=dict(username='member',name='Member',role='member',allowed_models=['test/model','vendor/second'])
    assert admin.put('/api/admin/users/'+member['id'],json=payload).status_code==200
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch()
        page=browser.new_page(viewport={'width':1440,'height':1000})
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        with TestClient(app.app) as transport:
            def route_request(route):
                request=route.request
                response=transport.request(request.method,request.url,content=request.post_data_buffer,
                    headers={k:v for k,v in request.headers.items() if k not in ('cookie','content-length')})
                route.fulfill(status=response.status_code,body=response.content,
                    headers={k:v for k,v in response.headers.items() if k not in ('content-length','content-encoding','transfer-encoding')})
            page.route('**/*',route_request)
            page.add_init_script("localStorage.setItem('cyberant-reading-size','22')")
            page.goto('http://testserver/')
            yield page,admin,member,payload
        browser.close()
        assert errors==[]

def login(page,role='member'):
    page.locator('#login-username').fill(role)
    page.locator('#login-password').fill('Test-password-12345')
    page.locator('#login-submit').click()
    expect(page.locator('#workspace')).to_be_visible()

def test_password_and_model_selection(browser_page):
    page,_,_,_=browser_page
    field=page.locator('#login-password');toggle=page.locator('#toggle-login-password')
    field.fill('temporary')
    toggle.focus();page.keyboard.press('Space')
    expect(field).to_have_attribute('type','text');expect(toggle).to_have_attribute('aria-pressed','true')
    expect(field).to_have_value('temporary');expect(page.locator('#workspace')).to_be_hidden()
    login(page)
    expect(field).to_have_value('');expect(field).to_have_attribute('type','password')
    expect(toggle).to_have_attribute('aria-pressed','false')
    assert page.locator('#font-smaller,#font-larger,#reading-size').count()==0
    assert page.locator('#new-chat').count()==1
    selector=page.locator('#chat-model');expect(selector).to_have_value('test/model')
    page.locator('#question').fill('DNS là gì?');page.locator('#send').click()
    expect(page.locator('.message.assistant')).to_have_count(1)
    assert page.locator('.message-text').evaluate('(e)=>getComputedStyle(e).fontSize')=='18px'
    selector.select_option('vendor/second')
    expect(selector).to_be_enabled();expect(selector).to_have_value('vendor/second')
    expect(page.locator('.message.assistant')).to_have_count(1)
    page.locator('#question').fill('DNS là gì?');page.locator('#send').click()
    expect(page.locator('.message.assistant')).to_have_count(2)
    expect(page.locator('.message-footer').last).to_contain_text('vendor/second')
    page.reload();expect(selector).to_have_value('vendor/second')
    expect(page.locator('.message.assistant')).to_have_count(2)
    for width in (1440,768,390,320):
        page.set_viewport_size({'width':width,'height':900})
        expect(selector).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'Horizontal overflow at {width}px'

def test_admin_checkbox_edit_and_warning(browser_page):
    page,_,member,_=browser_page
    login(page,'admin');page.locator('#users-nav').click()
    page.locator('[data-edit-user="'+member['id']+'"]').click()
    expect(page.locator('#user-models input:checked')).to_have_count(2)
    expect(page.locator('#user-model-count')).to_contain_text('2 model')
    page.locator('#user-models input').nth(0).uncheck()
    page.locator('#user-form button.primary').click()
    expect(page.locator('#user-form-title')).to_have_text('Tạo tài khoản')
    page.locator('[data-edit-user="'+member['id']+'"]').click()
    expect(page.locator('#user-models input:checked')).to_have_count(1)
    with app.connect() as db:db.execute('UPDATE users SET allowed_models=? WHERE id=?',(json.dumps(['vendor/second','retired/model']),member['id']))
    page.locator('#refresh-users').click()
    expect(page.locator('#users-table')).to_contain_text('retired/model')
    page.locator('[data-edit-user="'+member['id']+'"]').click()
    expect(page.locator('#user-models')).to_contain_text('Không còn cấu hình')
    expect(page.locator('#user-models input:checked')).to_have_count(2)

def test_disabled_during_request_and_revocation(browser_page):
    page,admin,member,payload=browser_page
    login(page);pending=[]
    page.route('**/api/chat',lambda route:pending.append(route))
    page.locator('#question').fill('DNS là gì?');page.locator('#send').click()
    expect(page.locator('#chat-model')).to_be_disabled();expect(page.locator('#send')).to_be_disabled()
    page.wait_for_function("document.querySelector('.thinking')!==null")
    assert pending
    pending[0].fulfill(status=503,content_type='application/json',body=json.dumps({'detail':'Mock provider failure'}))
    expect(page.locator('#chat-model')).to_be_enabled()
    assert len(pending)==1
    assert admin.put('/api/admin/users/'+member['id'],json={**payload,'allowed_models':['vendor/second']}).status_code==200
    page.evaluate('checkHealth()')
    expect(page.locator('#chat-model')).to_have_value('');expect(page.locator('#send')).to_be_disabled()
    expect(page.locator('#model-status')).to_contain_text('Hãy chọn lại')
    page.locator('#chat-model').select_option('vendor/second');expect(page.locator('#send')).to_be_enabled()
    with app.connect() as db:db.execute("UPDATE users SET allowed_models='[]' WHERE id=?",(member['id'],))
    page.evaluate('checkHealth()')
    expect(page.locator('#chat-model')).to_be_disabled();expect(page.locator('#send')).to_be_disabled()
    expect(page.locator('#model-status')).to_contain_text('Chưa có model khả dụng')
