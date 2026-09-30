"""OpenRouter only; the model allowlist is server-owned configuration."""
import json,re
import httpx
from fastapi import HTTPException
import config

def allowed_models(value):
    """Decode persisted permissions; malformed data must never grant access."""
    if isinstance(value,str):
        try:value=json.loads(value)
        except (ValueError,TypeError):return []
    if not isinstance(value,list):return []
    return list(dict.fromkeys(m for m in value if isinstance(m,str) and m))

def require_allowed(model,allowed):
    if not model or model not in allowed_models(allowed):
        raise HTTPException(403,'Model chưa được cấp hoặc đã bị thu hồi. Hãy chọn lại model được phép.')
    if model not in models():
        raise HTTPException(409,'Model không còn trong cấu hình. Hãy chọn lại model hoặc liên hệ quản trị.')
    return model


def init_permissions(connect):
    with connect() as c:
        cols={r[1] for r in c.execute('PRAGMA table_info(users)')}
        if 'allowed_models' not in cols:c.execute('ALTER TABLE users ADD COLUMN allowed_models TEXT')
        for row in c.execute('SELECT id,model FROM users WHERE allowed_models IS NULL').fetchall():
            c.execute('UPDATE users SET allowed_models=? WHERE id=?',(json.dumps([row['model']] if row['model'] else []),row['id']))

def models():
    values=config.env();result=[]
    primary=values.get('OPENROUTER_MODEL') or values.get('MODEL','')
    for value in [primary]+[v for k,v in sorted(values.items()) if re.fullmatch(r'(?:OPENROUTER_)?MODEL_?\d+',k)]:
        value=value.strip()
        if value and value not in result:result.append(value)
    return result

def settings(model=None):
    values=config.env();available=models()
    selected=model or (available[0] if available else '')
    if selected and selected not in available:raise ValueError('Model tài khoản không còn trong danh sách .env; liên hệ quản trị.')
    return dict(mode='openrouter',api_key=values.get('OPENROUTER_API_KEY') or values.get('API_KEY',''),model=selected,
                url='https://openrouter.ai/api/v1',input_budget=config.integer('RAG_INPUT_TOKENS',18000,2048,32000),
                output_budget=config.integer('RAG_OUTPUT_TOKENS',2400,64,8192),top_k=config.integer('RAG_TOP_K',6,2,12),
                parallel=config.integer('API_PARALLEL',4,1,16))

def public_settings():
    s=settings()
    return {k:v for k,v in s.items() if k not in ('api_key','url')}|{'models':models(),'configured':bool(s['api_key'] and s['model'])}

def headers(s):
    if not s['api_key'] or not s['model']:raise ValueError('Thiếu API_KEY hoặc MODEL trong .env')
    return {'Authorization':'Bearer '+s['api_key'],'X-Title':'CyberAnt Knowledge'}

class InvalidCompletion(ValueError):
    def __init__(self,usage):
        super().__init__('Model không trả nội dung hợp lệ');self.usage=usage

async def complete(messages,s,max_tokens):
    payload=dict(model=s['model'],messages=messages,temperature=0.1,max_tokens=max_tokens,reasoning={'enabled':False})
    # Never retry a billable request automatically.
    async with httpx.AsyncClient(timeout=httpx.Timeout(180,connect=15),trust_env=False) as client:
        response=await client.post(s['url']+'/chat/completions',headers=headers(s),json=payload)
        response.raise_for_status();data=response.json()
    usage=data.get('usage') or {}
    usage={k:usage[k] for k in ('prompt_tokens','completion_tokens','total_tokens','cost','prompt_tokens_details','completion_tokens_details') if k in usage}
    usage['generation_id']=data.get('id')
    try:
        choice=data['choices'][0];answer=choice['message']['content']
        if not isinstance(answer,str) or not answer.strip():raise ValueError()
    except (KeyError,IndexError,TypeError,ValueError):raise InvalidCompletion(usage)
    return answer,usage,choice.get('finish_reason')
