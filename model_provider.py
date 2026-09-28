"""One provider boundary. Credentials stay on the server, never in public settings."""
import os
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parent

def settings():
    values = {}
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.removeprefix('export ').split('=', 1)
            values[key.strip()] = value.strip().strip('\"\'')
    values.update(os.environ)
    key = values.get('OPENROUTER_API_KEY') or values.get('API_KEY', '')
    model = values.get('OPENROUTER_MODEL') or values.get('MODEL', '')
    mode = values.get('LLM_MODE', 'openrouter' if key and model else 'local').lower()
    if mode not in {'local', 'openrouter'}:
        raise ValueError('LLM_MODE phải là local hoặc openrouter')
    def number(name, default, lo, hi):
        return max(lo, min(hi, int(values.get(name, default))))
    return dict(mode=mode, api_key=key, model=model if mode=='openrouter' else 'cyberant-qwen3.5-9b',
                url='https://openrouter.ai/api/v1' if mode=='openrouter' else 'http://127.0.0.1:1234/v1',
                input_budget=number('RAG_INPUT_TOKENS', 6000, 2048, 32000),
                output_budget=number('RAG_OUTPUT_TOKENS', 1000, 256, 8192),
                top_k=number('RAG_TOP_K', 6, 2, 12), parallel=number('API_PARALLEL', 2, 1, 4))

def public_settings():
    s=settings()
    return {k:v for k,v in s.items() if k not in {'api_key','url'}} | {'configured':s['mode']=='local' or bool(s['api_key'] and s['model'])}

def headers(s):
    if s['mode']=='openrouter':
        if not s['api_key'] or not s['model']:
            raise ValueError('Thiếu OPENROUTER_API_KEY/API_KEY hoặc OPENROUTER_MODEL/MODEL trong .env')
        return {'Authorization':'Bearer '+s['api_key'], 'X-Title':'CyberAnt Knowledge'}
    key=ROOT/'data'/'model-api-key.txt'
    return {'Authorization':'Bearer '+key.read_text(encoding='utf8').strip()} if key.exists() else {}

async def complete(messages, s, max_tokens):
    payload=dict(model=s['model'], messages=messages, temperature=0.1, max_tokens=max_tokens)
    if s['mode']=='local':
        payload['chat_template_kwargs']={'enable_thinking':False}
    # Plain text works across providers; validate source references locally.
    # No automatic retries: a transport timeout must not silently double bill.
    async with httpx.AsyncClient(timeout=httpx.Timeout(180,connect=15),trust_env=False) as c:
        r=await c.post(s['url']+'/chat/completions',headers=headers(s),json=payload)
        r.raise_for_status()
        data=r.json()
    choice=data['choices'][0]
    answer=choice['message'].get('content')
    if not isinstance(answer,str) or not answer.strip():
        raise ValueError('Model không trả nội dung')
    usage=data.get('usage') or {}
    return answer, {k:usage[k] for k in ('prompt_tokens','completion_tokens','total_tokens','cost','prompt_tokens_details') if k in usage}, choice.get('finish_reason')
