"""Durable per-account monthly quota, atomic reservations and usage ledger.

Months use UTC. Token usage is independent of chat retention and model prices.
Uncertain network failures conservatively hold their reserved budget for review.
"""
from datetime import datetime,timezone
import json,math,secrets,time
from fastapi import HTTPException
import config,model_provider

def month():return datetime.now(timezone.utc).strftime('%Y-%m')

def init(connect):
    default_model=next(iter(model_provider.models()),'')
    default_limit=config.integer('DEFAULT_MONTHLY_TOKENS',1000000,0,10000000000)
    with connect() as c:
        cols={r[1] for r in c.execute('PRAGMA table_info(users)')}
        if 'model' not in cols:c.execute("ALTER TABLE users ADD COLUMN model TEXT NOT NULL DEFAULT ''")
        if 'monthly_token_limit' not in cols:c.execute(f'ALTER TABLE users ADD COLUMN monthly_token_limit INTEGER NOT NULL DEFAULT {default_limit}')
        c.execute("UPDATE users SET model=? WHERE model=''",(default_model,))
        c.executescript('''CREATE TABLE IF NOT EXISTS token_usage(
            id TEXT PRIMARY KEY,user_id TEXT NOT NULL,month TEXT NOT NULL,model TEXT NOT NULL,
            status TEXT NOT NULL,reserved_tokens INTEGER NOT NULL,prompt_tokens INTEGER,
            completion_tokens INTEGER,total_tokens INTEGER,cost REAL,generation_id TEXT,
            created REAL NOT NULL,updated REAL NOT NULL,note TEXT NOT NULL DEFAULT '');
            CREATE INDEX IF NOT EXISTS usage_owner_month ON token_usage(user_id,month);
            CREATE INDEX IF NOT EXISTS usage_created ON token_usage(created);''')

def recover(connect):
    # Called once at single-worker startup; never release potentially sent calls.
    with connect() as c:
        c.execute("UPDATE token_usage SET status='uncertain',note='Tiến trình dừng trước khi ghi usage',updated=? WHERE status='in_flight'",(time.time(),))
        c.execute("UPDATE token_usage SET status='cancelled',updated=? WHERE status='reserved'",(time.time(),))

def totals(c,user_id,period):
    row=c.execute('''SELECT COALESCE(SUM(CASE WHEN status='completed' THEN total_tokens ELSE 0 END),0),
        COALESCE(SUM(CASE WHEN status IN ('reserved','in_flight') THEN reserved_tokens ELSE 0 END),0),
        COALESCE(SUM(CASE WHEN status='uncertain' THEN reserved_tokens ELSE 0 END),0),
        COALESCE(SUM(prompt_tokens),0),COALESCE(SUM(completion_tokens),0),COALESCE(SUM(cost),0),COUNT(*)
        FROM token_usage WHERE user_id=? AND month=?''',(user_id,period)).fetchone()
    return dict(used_tokens=row[0],reserved_tokens=row[1],uncertain_tokens=row[2],prompt_tokens=row[3],completion_tokens=row[4],cost=row[5],requests=row[6])

def summary(connect,user_id,period=None):
    period=period or month()
    with connect() as c:
        user=c.execute('SELECT monthly_token_limit,model FROM users WHERE id=?',(user_id,)).fetchone()
        if not user:raise HTTPException(404,'Không có tài khoản')
        result=totals(c,user_id,period)
    return dict(**result,month=period,timezone='UTC',monthly_token_limit=user[0],model=user[1],
                remaining_tokens=max(0,user[0]-result['used_tokens']-result['reserved_tokens']-result['uncertain_tokens']))

def reserve(connect,user_id,model,input_tokens,output_tokens):
    period=month();id=secrets.token_hex(16);stamp=time.time()
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        user=c.execute('SELECT active,model,monthly_token_limit FROM users WHERE id=?',(user_id,)).fetchone()
        if not user or not user[0]:raise HTTPException(403,'Tài khoản đã bị khóa.')
        if user[1]!=model:raise HTTPException(409,'Model tài khoản vừa thay đổi; hãy gửi lại câu hỏi.')
        usage=totals(c,user_id,period)
        remaining=user[2]-usage['used_tokens']-usage['reserved_tokens']-usage['uncertain_tokens']
        output=min(output_tokens,remaining-input_tokens)
        if output<64:raise HTTPException(429,'Không đủ hạn mức token tháng cho lượt này. Liên hệ quản trị để tăng hạn mức.')
        c.execute('INSERT INTO token_usage(id,user_id,month,model,status,reserved_tokens,created,updated) VALUES(?,?,?,?,?,?,?,?)',
                  (id,user_id,period,model,'reserved',input_tokens+output,stamp,stamp))
    return id,output

def mark_sent(connect,id):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('''SELECT u.active,u.model,t.model,u.monthly_token_limit,t.user_id,t.month FROM token_usage t
                         JOIN users u ON u.id=t.user_id WHERE t.id=? AND t.status='reserved' ''',(id,)).fetchone()
        if not row or not row[0] or row[1]!=row[2]:raise HTTPException(409,'Tài khoản hoặc model đã thay đổi.')
        used=totals(c,row[4],row[5])
        if used['used_tokens']+used['reserved_tokens']+used['uncertain_tokens']>row[3]:raise HTTPException(429,'Hạn mức vừa thay đổi; không gửi lượt này.')
        c.execute("UPDATE token_usage SET status='in_flight',updated=? WHERE id=?",(time.time(),id))

def measured(usage):
    p,o=usage.get('prompt_tokens'),usage.get('completion_tokens')
    if isinstance(p,bool) or isinstance(o,bool) or not isinstance(p,int) or not isinstance(o,int) or p<0 or o<0:return None
    total=usage.get('total_tokens',p+o)
    if isinstance(total,bool) or not isinstance(total,int) or total<p+o:return None
    cost=usage.get('cost')
    if not isinstance(cost,(int,float)) or isinstance(cost,bool) or not math.isfinite(cost) or cost<0:cost=None
    return p,o,total,cost

def settle(connect,id,usage=None,rejected=False):
    usage=usage or {};counts=measured(usage)
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT status FROM token_usage WHERE id=?',(id,)).fetchone()
        if not row or row[0] not in ('reserved','in_flight'):return
        if counts:
            c.execute("UPDATE token_usage SET status='completed',prompt_tokens=?,completion_tokens=?,total_tokens=?,cost=?,generation_id=?,updated=? WHERE id=?",(*counts,usage.get('generation_id'),time.time(),id))
        else:
            status='cancelled' if rejected or row[0]=='reserved' else 'uncertain'
            c.execute('UPDATE token_usage SET status=?,generation_id=?,note=?,updated=? WHERE id=?',(status,usage.get('generation_id'),'Không có usage xác nhận' if status=='uncertain' else '',time.time(),id))

def reconcile(connect,id,prompt,completion,note):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT status FROM token_usage WHERE id=?',(id,)).fetchone()
        if not row or row[0]!='uncertain':raise HTTPException(409,'Chỉ đối soát lượt chưa rõ usage.')
        c.execute("UPDATE token_usage SET status='completed',prompt_tokens=?,completion_tokens=?,total_tokens=?,note=?,updated=? WHERE id=?",(prompt,completion,prompt+completion,note,time.time(),id))
