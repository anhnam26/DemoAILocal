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
        if 'app' in sys.modules:
            raise RuntimeError('Run this suite in its own Python process.')
        cls.temp = tempfile.TemporaryDirectory(prefix='cyberant-ui-')
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        cls.port = sock.getsockname()[1]
        sock.close()
        cls.base = f'http://127.0.0.1:{cls.port}'
        values = dict(APP_DATA_DIR=cls.temp.name, APP_ENV='development', APP_ORIGINS=cls.base,
                      OPENROUTER_MODEL=MODELS[0], OPENROUTER_MODEL2=MODELS[1],
                      OPENROUTER_API_KEY='fake-key-never-sent')
        cls.config_patch = patch('config.env', return_value=values)
        cls.config_patch.start()
        cls.module = importlib.import_module('app')
        cls.provider_calls = 0

        async def fake_complete(messages, settings, max_tokens):
            cls.provider_calls += 1
            await asyncio.sleep(.15)
            source_id = re.search(r'\[([A-Z0-9-]+)\]', messages[-1]['content']).group(1)
            return (f'## Kiểm thử giao diện\nNội dung **giả lập** có căn cứ [{source_id}].\n'
                    '| Hạng mục | Kết quả |\n| --- | --- |\n| Kiểm tra | Đạt |\n'
                    '```text\nKhông có cuộc gọi model thật\n```',
                    dict(prompt_tokens=80, completion_tokens=40, total_tokens=120), 'stop')

        cls.provider_patch = patch('model_provider.complete', side_effect=fake_complete)
        cls.provider_patch.start()
        with cls.module.connect() as c:
            import accounts
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
        cls.artifacts = ROOT / 'artifacts' / 'ui-review'
        cls.artifacts.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(10)
        cls.provider_patch.stop()
        cls.module.INSTANCE_LOCK.close()
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
        import accounts
        with self.module.connect() as c:
            c.execute("UPDATE users SET password_hash=? WHERE username='member'", (accounts.hash_password(PASSWORD),))

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
            page.locator('#question').fill('RMA là gì?')
            page.locator('#send').click()
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

