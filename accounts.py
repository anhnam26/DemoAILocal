"""Local password accounts, revocable sessions and administrator user management."""
import hashlib,hmac,json,re,secrets,time
import config,model_provider,token_usage
from pathlib import Path
from fastapi import APIRouter,HTTPException,Request,Response
from pydantic import BaseModel,Field
ROOT=Path(__file__).parent
BOOTSTRAP=config.data_dir()/'initial-accounts.json'
ROLES={'member':'Thành viên','admin':'Quản trị'}

def hash_password(password):
    salt=secrets.token_bytes(16)
    digest=hashlib.scrypt(password.encode(),salt=salt,n=32768,r=8,p=1,maxmem=128*1024*1024)
    return 'scrypt$32768$'+salt.hex()+'$'+digest.hex()

def verify(password,encoded):
    try:
        _,n,salt,digest=encoded.split('$')
        actual=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=int(n),r=8,p=1,maxmem=128*1024*1024)
        return hmac.compare_digest(actual,bytes.fromhex(digest))
    except (ValueError,TypeError):return False

def token_hash(token):return hashlib.sha256(token.encode()).hexdigest()
DUMMY_HASH=hash_password('unregistered-account-placeholder')

def init(connect):
    with connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,username TEXT UNIQUE NOT NULL,name TEXT NOT NULL,role TEXT NOT NULL,customers TEXT NOT NULL,password_hash TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created REAL NOT NULL,updated REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS login_attempts(identity TEXT PRIMARY KEY,failures INTEGER NOT NULL,window REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS sessions_created ON sessions(created);''')
        cols={r[1] for r in c.execute('PRAGMA table_info(sessions)')}
        for name,kind in [('user_id','TEXT'),('sid','TEXT'),('last_seen','REAL'),('ip','TEXT'),('agent','TEXT')]:
            if name not in cols:c.execute(f'ALTER TABLE sessions ADD COLUMN {name} {kind}')
        if c.execute('SELECT COUNT(*) FROM users').fetchone()[0]:return
        if BOOTSTRAP.exists():seeds=json.loads(BOOTSTRAP.read_text(encoding='utf8'))['accounts']
        else:
            values=config.env()
            if config.security()['production']:
                password=values.get('BOOTSTRAP_ADMIN_PASSWORD','')
                if len(password)<14:raise RuntimeError('Set BOOTSTRAP_ADMIN_PASSWORD (>=14 characters) for first production startup')
                seeds=[dict(username=values.get('BOOTSTRAP_ADMIN_USERNAME','admin'),password=password,role='admin',name='Quản trị hệ thống',customers=[])]
            else:
                seeds=[dict(username=name,password=secrets.token_urlsafe(15),role=role,name=label,customers=[]) for name,role,label in [('member','member','Thành viên'),('admin','admin','Quản trị hệ thống')]]
            BOOTSTRAP.parent.mkdir(exist_ok=True)
            if not config.security()['production']:
                BOOTSTRAP.write_text(json.dumps(dict(note='Chỉ dùng lần cài mới trên máy phát triển.',accounts=seeds),ensure_ascii=False,indent=2),encoding='utf8')
        for s in seeds:
            s['role']='admin' if s['role']=='admin' else 'member';s['customers']=[]
            c.execute('INSERT INTO users(id,username,name,role,customers,password_hash,active,created,updated) VALUES(?,?,?,?,?,?,1,?,?)',(secrets.token_hex(12),s['username'],s['name'],s['role'],json.dumps(s['customers']),hash_password(s['password']),time.time(),time.time()))

def public(row):
    customers=json.loads(row['customers'])
    return dict(id=row['id'],username=row['username'],name=row['name'],role=row['role'],customers=customers,customer='',title=ROLES[row['role']]+' • Kho tri thức chung',active=bool(row['active']),model=row['model'],allowed_models=model_provider.allowed_models(row['allowed_models']),monthly_token_limit=row['monthly_token_limit'])

def current(req,connect):
    token=token_hash(req.cookies.get('cyberant_session',''))
    with connect() as c:
        s=c.execute('SELECT * FROM sessions WHERE token=?',(token,)).fetchone()
        u=c.execute('SELECT * FROM users WHERE id=?',(s['user_id'],)).fetchone() if s and s['user_id'] else None
        if not s or not u or not u['active'] or time.time()-s['created']>43200:raise HTTPException(401,'Phiên đăng nhập không còn hiệu lực. Hãy đăng nhập bằng tài khoản và mật khẩu.')
        if time.time()-(s['last_seen'] or 0)>10:c.execute('UPDATE sessions SET last_seen=? WHERE token=?',(time.time(),token))
    return {**public(u),'token':token,'sid':s['sid'],'context_after':s['context_after'] or 0}

class Login(BaseModel):
    username:str=Field(min_length=1,max_length=64)
    password:str=Field(min_length=1,max_length=128)
class UserInput(BaseModel):
    username:str=Field(min_length=3,max_length=40,pattern=r'^[a-zA-Z0-9_.-]+$')
    name:str=Field(min_length=2,max_length=80)
    role:str
    customers:list[str]=Field(default_factory=list,max_length=10)
    password:str|None=Field(default=None,min_length=10,max_length=128)
    active:bool=True
    model:str|None=Field(default=None,max_length=200)
    allowed_models:list[str]|None=Field(default=None,max_length=200)
    monthly_token_limit:int=Field(default=1000000,ge=0,le=10000000000)
class PasswordInput(BaseModel):
    old_password:str=Field(min_length=1,max_length=128)
    new_password:str=Field(min_length=10,max_length=128)

def install(app,connect,user,audit):
    router=APIRouter()
    def admin(req):
        u=user(req)
        if u['role']!='admin':raise HTTPException(403,'Chỉ Quản trị được quản lý tài khoản và phiên đăng nhập.')
        return u
    def validate(data,row=None):
        if data.role not in ROLES:raise HTTPException(400,'Vai trò phải là thành viên hoặc quản trị.')
        available=model_provider.models()
        if data.allowed_models is None:
            data.allowed_models=([data.model] if data.model else model_provider.allowed_models(row['allowed_models']) if row else available[:1])
        data.allowed_models=list(dict.fromkeys(data.allowed_models))
        if not data.allowed_models or any(m not in available for m in data.allowed_models):
            raise HTTPException(400,'Chọn ít nhất một model thuộc danh sách cấu hình máy chủ.')
        if data.model is not None and data.model not in data.allowed_models:
            raise HTTPException(400,'Model mặc định phải thuộc danh sách được cấp.')
        if data.model is None:
            data.model=row['model'] if row and row['model'] in data.allowed_models else '' if row else data.allowed_models[0]
        return []
    @router.post('/api/login')
    def login(data:Login,req:Request,res:Response):
        identity=(req.client.host if req.client else 'local')+'|'+data.username.strip().lower()
        with connect() as c:
            attempt=c.execute('SELECT * FROM login_attempts WHERE identity=?',(identity,)).fetchone()
            if attempt and attempt['failures']>=8 and time.time()-attempt['window']<300:raise HTTPException(429,'Đăng nhập sai nhiều lần. Thử lại sau 5 phút.')
            u=c.execute('SELECT * FROM users WHERE username=? COLLATE NOCASE',(data.username.strip(),)).fetchone()
            verified=verify(data.password,u['password_hash'] if u else DUMMY_HASH)
            if not u or not verified or not u['active']:
                failures=attempt['failures']+1 if attempt and time.time()-attempt['window']<300 else 1
                window=attempt['window'] if attempt and time.time()-attempt['window']<300 else time.time()
                c.execute('INSERT OR REPLACE INTO login_attempts VALUES(?,?,?)',(identity,failures,window));c.commit()
                raise HTTPException(401,'Tên đăng nhập hoặc mật khẩu không đúng, hoặc tài khoản đã khóa.')
            c.execute('DELETE FROM login_attempts WHERE identity=?',(identity,))
            raw=secrets.token_urlsafe(32);token=token_hash(raw)
            c.execute('DELETE FROM sessions WHERE token=?',(token_hash(req.cookies.get('cyberant_session','')),))
            c.execute('INSERT INTO sessions(token,profile,created,user_id,sid,last_seen,ip,agent) VALUES(?,?,?,?,?,?,?,?)',(token,u['role'],time.time(),u['id'],secrets.token_hex(12),time.time(),req.client.host if req.client else 'local',req.headers.get('user-agent','')[:160]))
        res.set_cookie('cyberant_session',raw,httponly=True,samesite='strict',secure=config.security()['secure_cookie'],max_age=43200)
        audit('login',u['role'],u['username']);return public(u)
    @router.post('/api/logout')
    def logout(req:Request,res:Response):
        with connect() as c:c.execute('DELETE FROM sessions WHERE token=?',(token_hash(req.cookies.get('cyberant_session','')),))
        res.delete_cookie('cyberant_session',secure=config.security()['secure_cookie'],httponly=True,samesite='strict');return {'ok':True}
    @router.post('/api/heartbeat')
    def heartbeat(req:Request):
        u=user(req)
        return dict(ok=True,username=u['username'],server_time=time.time())
    @router.post('/api/account/password')
    def change_password(data:PasswordInput,req:Request,res:Response):
        u=user(req)
        with connect() as c:
            row=c.execute('SELECT * FROM users WHERE id=?',(u['id'],)).fetchone()
            if not verify(data.old_password,row['password_hash']):raise HTTPException(400,'Mật khẩu hiện tại không đúng.')
            c.execute('UPDATE users SET password_hash=?,updated=? WHERE id=?',(hash_password(data.new_password),time.time(),u['id']))
            c.execute('DELETE FROM sessions WHERE user_id=?',(u['id'],))
        res.delete_cookie('cyberant_session',secure=config.security()['secure_cookie'],httponly=True,samesite='strict');audit('password_changed',u['role'],u['username']);return dict(ok=True,message='Đã đổi mật khẩu và đăng xuất tất cả phiên của tài khoản.')
    @router.get('/api/admin/users')
    def users(req:Request):
        admin(req)
        with connect() as c:
            people=[public(r) for r in c.execute('SELECT * FROM users ORDER BY created')]
            sessions=[dict(r) for r in c.execute('SELECT s.sid,s.user_id,u.username,u.name,u.role,s.created,s.last_seen,s.ip,s.agent FROM sessions s JOIN users u ON s.user_id=u.id WHERE u.active=1 AND s.created>? ORDER BY s.last_seen DESC',(time.time()-43200,))]
        for s in sessions:s['online']=time.time()-(s['last_seen'] or 0)<75
        for u in people:
            u['online']=any(s['user_id']==u['id'] and s['online'] for s in sessions)
            u['usage']=token_usage.summary(connect,u['id'])
        return dict(users=people,sessions=sessions,models=model_provider.models(),month=token_usage.month(),online_count=sum(u['online'] for u in people),online_definition='Có hoạt động trong 75 giây gần nhất.')
    @router.post('/api/admin/users')
    def create(data:UserInput,req:Request):
        a=admin(req);customers=validate(data);password=data.password or secrets.token_urlsafe(15);id=secrets.token_hex(12)
        with connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT 1 FROM users WHERE username=? COLLATE NOCASE',(data.username,)).fetchone():raise HTTPException(409,'Tên đăng nhập đã tồn tại.')
            c.execute('INSERT INTO users(id,username,name,role,customers,password_hash,active,created,updated,model,monthly_token_limit,allowed_models) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(id,data.username.lower(),data.name,data.role,json.dumps(customers),hash_password(password),int(data.active),time.time(),time.time(),data.model,data.monthly_token_limit,json.dumps(data.allowed_models)))
        audit('user_create',a['role'],data.username);return dict(id=id,username=data.username.lower(),temporary_password=password)
    @router.put('/api/admin/users/{id}')
    def update(id:str,data:UserInput,req:Request):
        a=admin(req)
        with connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM users WHERE id=?',(id,)).fetchone()
            if not row:raise HTTPException(404,'Không có tài khoản.')
            customers=validate(data,row)
            if row['role']=='admin' and row['active'] and (not data.active or data.role!='admin') and c.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND active=1").fetchone()[0]<=1:raise HTTPException(400,'Phải giữ ít nhất một tài khoản quản trị hoạt động.')
            if c.execute('SELECT 1 FROM users WHERE username=? COLLATE NOCASE AND id<>?',(data.username,id)).fetchone():raise HTTPException(409,'Tên đăng nhập đã tồn tại.')
            c.execute('UPDATE users SET username=?,name=?,role=?,customers=?,active=?,password_hash=?,updated=?,model=?,monthly_token_limit=?,allowed_models=? WHERE id=?',(data.username.lower(),data.name,data.role,json.dumps(customers),int(data.active),hash_password(data.password) if data.password else row['password_hash'],time.time(),data.model,data.monthly_token_limit,json.dumps(data.allowed_models),id))
            if data.password or data.role!=row['role'] or not data.active or data.username.lower()!=row['username']:
                c.execute('DELETE FROM sessions WHERE user_id=?',(id,))
        audit('user_update',a['role'],json.dumps(dict(id=id,model=data.model,allowed_models=data.allowed_models,monthly_token_limit=data.monthly_token_limit)));return dict(ok=True)
    @router.post('/api/admin/users/{id}/reset-password')
    def reset(id:str,req:Request):
        a=admin(req);password=secrets.token_urlsafe(15)
        with connect() as c:
            if not c.execute('SELECT 1 FROM users WHERE id=?',(id,)).fetchone():raise HTTPException(404,'Không có tài khoản.')
            c.execute('UPDATE users SET password_hash=?,updated=? WHERE id=?',(hash_password(password),time.time(),id));c.execute('DELETE FROM sessions WHERE user_id=?',(id,))
        audit('password_reset',a['role'],id);return dict(temporary_password=password)
    @router.delete('/api/admin/sessions/{sid}')
    def revoke(sid:str,req:Request):
        a=admin(req)
        with connect() as c:c.execute('DELETE FROM sessions WHERE sid=?',(sid,))
        audit('session_revoke',a['role'],sid);return dict(ok=True)
    app.include_router(router)
