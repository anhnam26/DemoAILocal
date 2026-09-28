import json,httpx,model_provider
response=httpx.get('https://openrouter.ai/api/v1/models',timeout=30,trust_env=False);response.raise_for_status()
catalog={m['id']:m for m in response.json()['data']}
for name in model_provider.models():
    item=catalog.get(name)
    print(json.dumps({'model':name,'in_catalog':item is not None,'context_length':item.get('context_length') if item else None},ensure_ascii=False))
