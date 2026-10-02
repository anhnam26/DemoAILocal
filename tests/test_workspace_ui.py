"""Isolated API + optional browser checks. Never reads .env or calls a provider.
Run: python -m unittest discover -s tests -p test_workspace_ui.py -v
Browser checks use an installed Playwright/Chromium; no runtime dependency added.
"""
import asyncio
import importlib
import json
import re
import socket
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
import uvicorn

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = 'Isolated-test-password-2026'
MODELS = ['test/ocean-one', 'test/ocean-two']


class WorkspaceUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import sys
        if 'cyberant.app' in sys.modules:
            raise RuntimeError('Run this suite in its own Python process.')
        cls.temp = tempfile.TemporaryDirectory(prefix='cyberant-ui-')
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        cls.port = sock.getsockname()[1]
        sock.close()
        cls.base = f'http://127.0.0.1:{cls.port}'
        cls.data=Path(cls.temp.name)/'runtime'
        values = dict(APP_DATA_DIR=str(cls.data), APP_ENV='development', APP_ORIGINS=cls.base,
                      BOOTSTRAP_ADMIN_PASSWORD=PASSWORD,
                      OPENROUTER_MODEL=MODELS[0], OPENROUTER_MODEL2=MODELS[1],
                      OPENROUTER_API_KEY='fake-key-never-sent')
        cls.config_patch = patch('cyberant.config.env', return_value=values)
        cls.config_patch.start()
        from cyberant import operations
        operations.initialize(cls.data)
        cls.module = importlib.import_module('cyberant.app')
        cls.provider_calls = 0

        async def fake_complete(messages, settings, max_tokens):
            cls.provider_calls += 1
            await asyncio.sleep(.15)
            source_id = re.search(r'\[([A-Z0-9-]+)\]', messages[-1]['content']).group(1)
            return (f'## Kiểm thử giao diện\nNội dung **giả lập** có căn cứ [{source_id}].\n'
                    '| Hạng mục | Kết quả |\n| --- | --- |\n| Kiểm tra | Đạt |\n'
                    '```text\nKhông có cuộc gọi model thật\n```',
                    dict(prompt_tokens=80, completion_tokens=40, total_tokens=120), 'stop')

        cls.provider_patch = patch('cyberant.model_provider.complete', side_effect=fake_complete)
        cls.provider_patch.start()
        with cls.module.connect() as c:
            from cyberant import accounts
            c.execute('INSERT INTO users(id,username,name,role,customers,password_hash,active,created,updated,model,monthly_token_limit,allowed_models) VALUES(?,?,?,?,?,?,1,?,?,?,?,?)',
                      ('fixture-member','member','Thành viên','member','[]',accounts.hash_password(PASSWORD),time.time(),time.time(),MODELS[0],1000000,json.dumps(MODELS)))
            c.execute('UPDATE users SET password_hash=?,allowed_models=?,model=?',
                      (accounts.hash_password(PASSWORD), json.dumps(MODELS), MODELS[0]))
            member = c.execute("SELECT id FROM users WHERE username='member'").fetchone()['id']
            stamp = datetime.now(timezone.utc)
            for i in range(56):
                updated = (stamp - timedelta(days=i)).isoformat()
                c.execute('INSERT INTO conversations VALUES(?,?,?,?,?)',
                          (f'fixture-{i:03}', member, f'Lịch sử mẫu {i:02}', updated, updated))
        cls.server = uvicorn.Server(uvicorn.Config(cls.module.app, host='127.0.0.1', port=cls.port,
                                                   log_level='error'))
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()
        for _ in range(150):
            if cls.server.started:
                break
            time.sleep(.1)
        if not cls.server.started:
            raise RuntimeError('Isolated test server failed to start')
        cls.artifacts = Path(cls.temp.name) / 'ui-review'
        cls.artifacts.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(10)
        cls.provider_patch.stop()
        cls.config_patch.stop()
        cls.temp.cleanup()

    def client(self, username='member'):
        client = httpx.Client(base_url=self.base, timeout=30)
        self.addCleanup(client.close)
        response = client.post('/api/login', json=dict(username=username, password=PASSWORD))
        self.assertEqual(response.status_code, 200, response.text)
        return client

    def test_01_api_permissions_history_and_citations(self):
        member, admin = self.client(), self.client('admin')
        response = member.get('/')
        self.assertIn("script-src 'self'", response.headers['content-security-policy'])
        self.assertEqual(member.get('/api/ready').json()['status'],'ready')
        oversized=member.post('/api/login',content=iter([b'x'*1_100_000,b'x'*1_100_000]),headers={'Content-Type':'application/json'})
        self.assertEqual(oversized.status_code,413)
        self.assertNotIn('unsafe-inline', response.headers['content-security-policy'])
        self.assertEqual(member.get('/static/Logo.png').content, (ROOT / 'static' / 'Logo.png').read_bytes())
        self.assertEqual(member.get('/Logo.png').status_code, 404)
        self.assertNotIn('/static/ocean.js', response.text)
        self.assertNotIn('id="ocean"', response.text)
        for name in ('theme.js', 'modern.css'):
            self.assertEqual(member.get('/static/' + name).status_code, 200)
        self.assertEqual(member.get('/api/admin/users').status_code, 403)
        self.assertEqual(admin.get('/api/admin/users').status_code, 200)
        self.assertEqual(member.get('/api/model').json()['allowed_models'], MODELS)
        self.assertEqual(member.put('/api/model', json={'model': MODELS[1]}).status_code, 200)
        self.assertEqual(member.put('/api/model', json={'model': 'forbidden/model'}).status_code, 403)
        first = member.get('/api/conversations').json()
        self.assertEqual(len(first['items']), 50)
        self.assertTrue(first['has_more'])
        self.assertEqual(len(member.get('/api/conversations?offset=50').json()['items']), 6)
        self.assertEqual(len(member.get('/api/conversations?q=55').json()['items']), 1)
        new_id = member.post('/api/conversations').json()['id']
        self.assertEqual(admin.get('/api/conversations/' + new_id).status_code, 404)
        self.assertEqual(admin.delete('/api/conversations/' + new_id).status_code, 404)
        answer = member.post('/api/chat', json=dict(question='RMA là gì?', conversation_id=new_id, model=MODELS[1]))
        self.assertEqual(answer.status_code, 200, answer.text)
        data = answer.json()
        self.assertTrue(data['sources'])
        self.assertTrue(data['citations_verified'])
        self.assertEqual(data['model'], MODELS[1])
        self.assertEqual(member.get('/api/conversations/' + new_id).json()['messages'][0]['question'], 'RMA là gì?')
        used = member.get('/api/account/usage').json()['used_tokens']
        self.assertGreaterEqual(used, 120)
        self.assertEqual(member.delete('/api/conversations/' + new_id).status_code, 200)
        self.assertEqual(member.get('/api/account/usage').json()['used_tokens'], used)
        # Role is presentation only, mock provider remains the only generation path.
        invalid=member.post('/api/chat',json=dict(question='SOW BOM Managed Service',audience='admin'))
        self.assertEqual(invalid.status_code,422)
        service=member.post('/api/chat',json=dict(question='SOW BOM Managed Service',audience='engineering'))
        self.assertEqual(service.status_code,200,service.text)
        result=service.json()
        self.assertEqual(result['retrieval']['intent'],'sow_bom')
        self.assertEqual(result['diagnostics']['packing']['audience'],'engineering')
        self.assertEqual(result['api_calls'],1)
        self.assertFalse(result['grounding_verified'])
        self.assertEqual(result['retrieval']['packed_coverage']['verification'],'evidence_types_only_not_entailment')
        member.delete('/api/conversations/'+result['conversation_id'])
        with self.module.connect() as c:
            c.execute("UPDATE users SET monthly_token_limit=0 WHERE username='member'")
        before = self.provider_calls
        blocked = member.post('/api/chat', json=dict(question='RMA là gì?', model=MODELS[1]))
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(self.provider_calls, before)
        with self.module.connect() as c:
            c.execute("UPDATE users SET monthly_token_limit=1000000 WHERE username='member'")
        # The rejected turn may create an empty conversation, but must not charge usage.
        for item in member.get('/api/conversations').json()['items']:
            if not item['id'].startswith('fixture-'):
                member.delete('/api/conversations/' + item['id'])
        self.assertEqual(member.post('/api/logout').status_code, 200)
        self.assertEqual(member.get('/api/me').status_code, 401)

    def test_05_password_permissions_and_admin_reset(self):
        member, admin = self.client(), self.client('admin')
        member_session = self.client()
        anonymous = httpx.Client(base_url=self.base, timeout=30)
        self.addCleanup(anonymous.close)
        payload = dict(old_password=PASSWORD, new_password=PASSWORD + '-changed')
        self.assertEqual(anonymous.post('/api/account/password', json=payload).status_code, 401)
        for old in (PASSWORD, 'wrong-password'):
            response = member.post('/api/account/password', json={**payload, 'old_password': old})
            self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(member.get('/api/me').status_code, 200)
        self.assertEqual(member_session.get('/api/me').status_code, 200)
        member_id = member.get('/api/me').json()['id']
        response = member.post(f'/api/admin/users/{member_id}/reset-password')
        self.assertEqual(response.status_code, 403)
        response = admin.post(f'/api/admin/users/{member_id}/reset-password')
        self.assertEqual(response.status_code, 200, response.text)
        reset_password = response.json()['temporary_password']
        for client in (member, member_session):
            self.assertEqual(client.get('/api/me').status_code, 401)
        self.assertEqual(anonymous.post('/api/login', json=dict(username='member', password=PASSWORD)).status_code, 401)
        self.assertEqual(anonymous.post('/api/login', json=dict(username='member', password=reset_password)).status_code, 200)
        self.assertEqual(anonymous.post('/api/account/password', json=dict(old_password=reset_password, new_password=PASSWORD)).status_code, 403)
        admin_session = self.client('admin')
        self.assertEqual(admin.post('/api/account/password', json={**payload, 'old_password': 'wrong-password'}).status_code, 400)
        response = admin.post('/api/account/password', json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        for client in (admin, admin_session):
            self.assertEqual(client.get('/api/me').status_code, 401)
        self.assertEqual(admin.post('/api/login', json=dict(username='admin', password=PASSWORD)).status_code, 401)
        self.assertEqual(admin.post('/api/login', json=dict(username='admin', password=payload['new_password'])).status_code, 200)
        self.assertEqual(admin.post('/api/account/password', json=dict(old_password=payload['new_password'], new_password=PASSWORD)).status_code, 200)
        # Restore only the isolated fixture so tests can also be rerun independently.
        from cyberant import accounts
        with self.module.connect() as c:
            c.execute("UPDATE users SET password_hash=? WHERE username='member'", (accounts.hash_password(PASSWORD),))

    def test_06_login_aurora(self):
        try:
            from playwright.sync_api import sync_playwright, expect
        except ImportError:
            self.skipTest('Optional Playwright not installed')
        with sync_playwright() as p:
            browser = self.browser(p)
            context = browser.new_context(viewport={'width': 1440, 'height': 960}, color_scheme='light')
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.add_init_script("""window.auroraFrames=0;window.cspErrors=[];
                const raf=window.requestAnimationFrame.bind(window);
                window.requestAnimationFrame=callback=>raf(time=>{window.auroraFrames++;callback(time)});
                document.addEventListener('securitypolicyviolation',e=>cspErrors.push(e.violatedDirective));""")
            page.goto(self.base)
            expect(page.locator('.login-message h1')).to_have_text('TRA CỨUNỘI BỘ.')
            expect(page.locator('.login-message p')).to_have_count(0)
            expect(page.locator('.login-aurora')).to_have_attribute('aria-hidden', 'true')
            expect(page.locator('.login-aurora')).to_have_css('pointer-events', 'none')
            self.assertFalse(page.evaluate("performance.getEntriesByType('resource').some(r=>r.name.endsWith('/ocean.js'))"))
            form_box = page.locator('.login-form').bounding_box()
            title_box = page.locator('.login-message h1').bounding_box()
            glow_box = page.locator('.aurora-glow').bounding_box()
            sheen_box = page.locator('.aurora-sheen').bounding_box()
            cell_state = """()=>Array.from(document.querySelectorAll('.aurora-cell'),el=>{
                const box=el.getBoundingClientRect();
                return {x:box.x,y:box.y,width:box.width,height:box.height,opacity:Number(getComputedStyle(el).opacity)};
            })"""
            no_colour = "()=>Array.from(document.querySelectorAll('.aurora-cell')).every(el=>Number(getComputedStyle(el).opacity)===0)"
            palettes = []
            for theme in ('light', 'dark'):
                if theme == 'dark':
                    page.locator('.login-theme').click()
                expect(page.locator('html')).to_have_attribute('data-theme', theme)
                palettes.append(page.locator('.aurora-glow').evaluate('(el)=>getComputedStyle(el).backgroundImage'))
                page.locator('#login').dispatch_event('pointerleave')
                page.wait_for_function(no_colour)
                clip = {'x': 60, 'y': 760, 'width': 220, 'height': 160}
                before_image = page.screenshot(clip=clip)
                page.mouse.move(140, 840)
                page.wait_for_timeout(1100)
                before = page.evaluate(cell_state)
                self.assertTrue(any(cell['opacity'] > .2 for cell in before))
                self.assertNotEqual(page.screenshot(clip=clip), before_image, 'Hovered background must visibly change colour')
                for cell in before:
                    distance = ((cell['x'] + cell['width']/2 - 140)**2 + (cell['y'] + cell['height']/2 - 840)**2)**.5
                    if distance >= 180:
                        self.assertEqual(cell['opacity'], 0, 'Distant background must stay unchanged')
                page.screenshot(path=str(self.artifacts / f'login-local-colour-{theme}.png'))
                page.mouse.move(680, 720)
                after = page.evaluate(cell_state)
                self.assertTrue(any(old['opacity'] > .2 and new['opacity'] > 0 for old, new in zip(before, after)),
                                'Previous colour must fade at its original position, not move with the pointer')
                page.wait_for_timeout(2600)
                after = page.evaluate(cell_state)
                self.assertEqual([{k: v for k, v in cell.items() if k != 'opacity'} for cell in before],
                                 [{k: v for k, v in cell.items() if k != 'opacity'} for cell in after])
                for old, new in zip(before, after):
                    if old['opacity'] > 0:
                        self.assertEqual(new['opacity'], 0, 'Old colour must fade back to the original background')
                self.assertTrue(any(cell['opacity'] > .2 for cell in after))
                self.assertEqual(page.locator('.aurora-glow').bounding_box(), glow_box)
                self.assertEqual(page.locator('.aurora-sheen').bounding_box(), sheen_box)
                expect(page.locator('.aurora-glow')).to_have_css('transform', 'none')
                expect(page.locator('.aurora-sheen')).to_have_css('transform', 'none')
                frames = page.evaluate('auroraFrames')
                page.wait_for_timeout(250)
                self.assertEqual(page.evaluate('auroraFrames'), frames, 'Animation must stop when settled')
                self.assertEqual(page.locator('.login-form').bounding_box(), form_box)
                self.assertEqual(page.locator('.login-message h1').bounding_box(), title_box)
                self.assert_theme_top_right(page, '.login-theme')
                page.screenshot(path=str(self.artifacts / f'login-aurora-{theme}.png'))
            self.assertNotEqual(*palettes)
            page.locator('#login').dispatch_event('pointerleave')
            page.wait_for_function(no_colour)
            page.mouse.move(120, 120)
            page.emulate_media(reduced_motion='reduce')
            expect(page.locator('.aurora-glow')).to_have_css('transform', 'none')
            expect(page.locator('.aurora-cell')).to_have_count(0)
            frames = page.evaluate('auroraFrames')
            page.mouse.move(620, 800)
            page.wait_for_timeout(250)
            expect(page.locator('.aurora-cell')).to_have_count(0)
            self.assertEqual(page.evaluate('auroraFrames'), frames)
            page.emulate_media(reduced_motion='no-preference')
            # Media-query change events are delivered asynchronously on a render frame.
            page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
            page.mouse.move(300, 400)
            page.wait_for_function("()=>Array.from(document.querySelectorAll('.aurora-cell')).some(el=>Number(el.style.opacity)>.1)")
            # Exercise the hidden-tab lifecycle without relying on headless window focus.
            page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'))")
            expect(page.locator('.aurora-cell')).to_have_count(0)
            frames = page.evaluate('auroraFrames')
            page.mouse.move(500, 600)
            page.wait_for_timeout(250)
            self.assertEqual(page.evaluate('auroraFrames'), frames)
            page.evaluate("delete document.hidden;document.dispatchEvent(new Event('visibilitychange'))")
            page.locator('#login-username').fill('member')
            page.locator('#login-password').fill(PASSWORD)
            page.locator('#login-submit').click()
            expect(page.locator('#workspace')).to_be_visible()
            expect(page.locator('.aurora-cell')).to_have_count(0)
            frames = page.evaluate('auroraFrames')
            page.mouse.move(400, 400)
            page.wait_for_timeout(250)
            self.assertEqual(page.evaluate('auroraFrames'), frames)
            self.assertEqual(page.evaluate('cspErrors'), [])
            self.assertEqual(errors, [])
            mobile = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True,
                                         has_touch=True, reduced_motion='no-preference', color_scheme='light')
            phone = mobile.new_page()
            phone.goto(self.base)
            for theme in ('light', 'dark'):
                if theme == 'dark':
                    phone.locator('.login-theme').tap()
                expect(phone.locator('html')).to_have_attribute('data-theme', theme)
                phone.locator('#login').dispatch_event('pointermove', {'pointerType': 'touch', 'clientX': 100, 'clientY': 200})
                expect(phone.locator('.aurora-glow')).to_have_css('transform', 'none')
                self.assertEqual(phone.locator('.aurora-glow').evaluate('(el)=>el.style.transform'), '')
                expect(phone.locator('.aurora-cell')).to_have_count(0)
                self.assertFalse(phone.evaluate('document.documentElement.scrollWidth > innerWidth'))
                phone.screenshot(path=str(self.artifacts / f'login-aurora-mobile-{theme}.png'))
            browser.close()

    def browser(self, playwright):
        try:
            return playwright.chromium.launch(headless=True)
        except Exception as exc:
            self.skipTest('Installed Chromium unavailable: ' + str(exc))

    def assert_theme_top_right(self, page, selector):
        button = page.locator(selector)
        self.assertTrue(button.is_visible())
        box = button.bounding_box()
        self.assertLessEqual(page.viewport_size['width'] - box['x'] - box['width'], 32)
        self.assertGreaterEqual(page.viewport_size['width'] - box['x'] - box['width'], 0)
        self.assertLessEqual(box['y'], 24)

    def login(self, page, username='member', password=PASSWORD):
        page.goto(self.base)
        page.locator('#login-username').fill(username)
        page.locator('#login-password').fill(password)
        page.locator('#login-submit').click()
        page.locator('#workspace').wait_for(state='visible')
        page.wait_for_function('()=>!conversationLoading && !historyLoading')

    def test_02_desktop_browser(self):
        try:
            from playwright.sync_api import sync_playwright, expect
        except ImportError:
            self.skipTest('Optional Playwright not installed')
        with sync_playwright() as p:
            browser = self.browser(p)
            context = browser.new_context(viewport={'width': 1440, 'height': 960}, color_scheme='light')
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.add_init_script("window.cspErrors=[];document.addEventListener('securitypolicyviolation',e=>cspErrors.push(e.violatedDirective));")
            page.goto(self.base)
            expect(page.locator('html')).to_have_attribute('data-theme', 'light')
            self.assert_theme_top_right(page, '.login-theme')
            expect(page.locator('#ocean')).to_have_count(0)
            page.screenshot(path=str(self.artifacts / 'login-light.png'))
            page.locator('.login-theme').click()
            page.reload()
            expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
            page.mouse.move(250, 600)
            page.screenshot(path=str(self.artifacts / 'login-dark.png'))
            self.login(page)
            expect(page.locator('#user-role')).to_have_text('Thành viên')
            self.assert_theme_top_right(page, '.header-theme')
            expect(page.locator('#sidebar-close')).to_have_count(0)
            expect(page.locator('#sidebar [data-theme-toggle]')).to_have_count(0)
            page.locator('#sidebar-toggle').click()
            self.assert_theme_top_right(page, '.header-theme')
            page.locator('#sidebar-toggle').click()
            expect(page.locator('#admin-navigation')).to_be_hidden()
            self.assertEqual(page.locator('.source-panel').count(), 0)
            expect(page.locator('[data-conversation]')).to_have_count(50)
            page.locator('#history-more').click()
            expect(page.locator('[data-conversation]')).to_have_count(56)
            page.locator('#history-search').fill('55')
            expect(page.locator('[data-conversation]')).to_have_count(1)
            page.locator('[data-conversation]').click()
            expect(page.locator('[aria-current=true]')).to_have_count(1)
            page.locator('#new-chat').click()
            expect(page.locator('#history-search')).to_have_value('')
            page.locator('#chat-model').select_option(MODELS[0])
            page.wait_for_function('()=>!modelSaving')
            expect(page.locator('#chat-audience')).to_be_visible()
            page.locator('#chat-audience').select_option('sales')
            page.locator('#question').fill('RMA là gì?')
            with page.expect_request(lambda request: request.url.endswith('/api/chat') and request.method=='POST') as request:
                page.locator('#send').click()
            self.assertEqual(request.value.post_data_json['audience'],'sales')
            expect(page.locator('.inline-citation').first).to_be_visible(timeout=30000)
            page.wait_for_function('()=>!busy && !historyLoading')
            expect(page.locator('[aria-current=true]')).to_contain_text('RMA là gì?')
            page.screenshot(path=str(self.artifacts / 'chat-dark.png'))
            page.locator('.header-theme').click()
            page.wait_for_timeout(200)  # Allow the existing button color transition to finish.
            page.screenshot(path=str(self.artifacts / 'chat-light.png'))
            page.locator('.message-footer [data-doc]').first.click()
            expect(page.locator('#document-modal')).to_be_visible()
            page.locator('#close-modal').click()
            page.reload()
            expect(page.locator('.inline-citation').first).to_be_visible()
            page.once('dialog', lambda dialog: dialog.dismiss())
            page.locator('.conversation-entry.active .delete-conversation').click()
            expect(page.locator('.message.assistant')).to_have_count(1)
            page.once('dialog', lambda dialog: dialog.accept())
            page.locator('.conversation-entry.active .delete-conversation').click()
            expect(page.locator('#welcome')).to_be_visible()
            page.locator('#profile-toggle').click()
            expect(page.locator('#account-nav')).to_be_hidden()
            page.evaluate("switchView('account')")
            expect(page.locator('#view-account')).to_be_hidden()
            expect(page.locator('#view-chat')).to_be_visible()
            page.locator('#logout').click()
            expect(page.locator('#login')).to_be_visible()
            self.login(page, 'admin')
            expect(page.locator('#admin-navigation')).to_be_visible()
            page.locator('#users-nav').click()
            expect(page.locator('#users-table table')).to_be_visible()
            page.locator('#system-nav').click()
            expect(page.locator('#provider-summary')).to_contain_text(MODELS[0])
            self.assertEqual(errors, [])
            self.assertEqual(page.evaluate('cspErrors'), [])
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'))
            browser.close()


    def test_03_mobile_reduced_motion_and_password(self):
        try:
            from playwright.sync_api import sync_playwright, expect
        except ImportError:
            self.skipTest('Optional Playwright not installed')
        with sync_playwright() as p:
            browser = self.browser(p)
            context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True,
                                          has_touch=True, reduced_motion='reduce', color_scheme='dark')
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(self.base)
            expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
            expect(page.locator('#ocean')).to_have_count(0)
            self.assert_theme_top_right(page, '.login-theme')
            page.screenshot(path=str(self.artifacts / 'login-mobile.png'))
            self.login(page)
            expect(page.locator('#sidebar-toggle')).to_have_attribute('aria-expanded', 'false')
            page.locator('#sidebar-toggle').click()
            expect(page.locator('#sidebar-close')).to_have_count(0)
            expect(page.locator('#new-chat')).to_be_focused()
            page.keyboard.press('Escape')
            expect(page.locator('#sidebar-toggle')).to_be_focused()
            page.locator('#sidebar-toggle').click()
            page.locator('#new-chat').click()
            expect(page.locator('#sidebar-toggle')).to_have_attribute('aria-expanded', 'false')
            expect(page.locator('#question')).to_be_focused()
            page.screenshot(path=str(self.artifacts / 'chat-mobile.png'))
            self.assertFalse(page.evaluate('document.documentElement.scrollWidth > innerWidth'))
            box = page.locator('#chat-form').bounding_box()
            self.assertLessEqual(box['y'] + box['height'], 844)
            page.locator('#sidebar-toggle').click()
            page.locator('#profile-toggle').click()
            expect(page.locator('#account-nav')).to_be_hidden()
            page.locator('#logout').click()
            expect(page.locator('#login')).to_be_visible()
            self.login(page, 'admin')
            self.assert_theme_top_right(page, '.header-theme')
            page.locator('.header-theme').click()
            expect(page.locator('html')).to_have_attribute('data-theme', 'light')
            page.locator('#sidebar-toggle').click()
            page.locator('#profile-toggle').click()
            page.locator('#account-nav').click()
            expect(page.locator('#password-form')).to_be_visible()
            self.assertEqual(errors, [])
            browser.close()

    def test_04_long_history_network_failure_and_storage_fallback(self):
        try:
            from playwright.sync_api import sync_playwright, expect
        except ImportError:
            self.skipTest('Optional Playwright not installed')
        admin = self.client('admin')
        conversation = admin.post('/api/conversations').json()['id']
        payload = dict(answer='Nội dung lưu để kiểm tra phân trang.', sources=[], needs_review=False,
                       mode='Fixture', elapsed=0, model=MODELS[0])
        with self.module.connect() as c:
            user = c.execute("SELECT id FROM users WHERE username='admin'").fetchone()['id']
            for i in range(105):
                c.execute('INSERT INTO chats(session,question,result,ts,user_id,conversation_id) VALUES(?,?,?,?,?,?)',
                          ('fixture', f'Tin nhắn {i:03}', json.dumps(payload), self.module.now(), user, conversation))
        with sync_playwright() as p:
            browser = self.browser(p)
            page = browser.new_page(viewport={'width': 1280, 'height': 800}, color_scheme='dark')
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new Error('Storage denied')}})")
            self.login(page, 'admin')
            expect(page.locator('.message.assistant')).to_have_count(100)
            page.locator('#older-messages').click()
            expect(page.locator('.message.assistant')).to_have_count(105)
            expect(page.locator('#older-messages')).to_be_hidden()
            page.locator('.header-theme').click()
            expect(page.locator('html')).to_have_attribute('data-theme', 'light')
            page.route('**/api/conversations?*', lambda route: route.abort())
            page.locator('#refresh-history').click()
            expect(page.locator('#history-status')).to_contain_text('Không tải được')
            page.unroute('**/api/conversations?*')
            page.locator('#refresh-history').click()
            expect(page.locator('#history-status')).to_have_text('')
            page.locator('#history-search').fill('not-a-conversation')
            expect(page.locator('.history-empty')).to_contain_text('Không tìm thấy')
            page.locator('#history-search').fill('')
            expect(page.locator('[data-conversation]')).to_have_count(1)
            # Mobile focus remains in the drawer, including when tabbing backwards.
            page.set_viewport_size({'width': 390, 'height': 700})
            page.locator('#sidebar-toggle').click()
            page.locator('#new-chat').focus()
            page.keyboard.press('Shift+Tab')
            expect(page.locator('#profile-toggle')).to_be_focused()
            page.keyboard.press('Tab')
            expect(page.locator('#new-chat')).to_be_focused()
            self.assertEqual(errors, [])
            browser.close()
        admin.delete('/api/conversations/' + conversation)

