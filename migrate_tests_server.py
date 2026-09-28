from pathlib import Path
p=Path('test_app.py');s=p.read_text(encoding='utf8')
s=s.replace("    app.init();app.ACTIVE_CONVERSATIONS.clear()\n",'')
s=s.replace("    async def complete(messages,cfg,max_tokens):", "    monkeypatch.setenv('APP_ENV','development')\n    monkeypatch.setenv('APP_ORIGINS','http://testserver,http://localhost:8088,http://127.0.0.1:8088')\n    app.init();app.ACTIVE_CONVERSATIONS.clear()\n    async def complete(messages,cfg,max_tokens):",1)
s=s.replace("health=TestClient(app.app).get('/api/health').json()", "health=client().get('/api/model').json()")
s=s.replace("health['mode']=='openrouter' and health['readiness']=='configured'","health['mode']=='openrouter' and health['configured']")
p.write_text(s,encoding='utf8')
p=Path('test_accounts_system.py');s=p.read_text(encoding='utf8').replace('import app,system_runtime','import app')
start=s.index('def test_admin_config_and_provider_boundary');s=s[:start]+'''def test_admin_system_permissions_and_removed_local():
    a,m=client('admin'),client()
    assert m.get('/api/admin/system').status_code==403
    assert m.get('/api/admin/usage').status_code==403
    assert a.get('/api/admin/system').status_code==200
    assert a.post('/api/admin/system/model',json={'action':'start'}).status_code==404
    assert a.put('/api/admin/system/provider',json={'mode':'local'}).status_code==404
'''
p.write_text(s,encoding='utf8')
p=Path('test_rag.py');s=p.read_text(encoding='utf8').replace("Path('data/knowledge_documents.json')","Path('knowledge/documents.json')")
s=s.replace("monkeypatch.setattr(model_provider,'ROOT',tmp_path)","monkeypatch.setattr(model_provider.config,'ROOT',tmp_path)")
s=s.replace("    monkeypatch.setenv('LLM_MODE','local');assert model_provider.settings()['url'].startswith('http://127.0.0.1')", "    monkeypatch.setenv('MODEL1','vendor/second');assert 'vendor/second' in model_provider.models()\n    monkeypatch.setenv('LLM_MODE','local');assert model_provider.settings()['url'].startswith('https://openrouter.ai')")
s=s.replace("@pytest.mark.parametrize('mode',['local','openrouter'])","@pytest.mark.parametrize('mode',['openrouter'])")
p.write_text(s,encoding='utf8')
