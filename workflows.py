import json,secrets,time,math,hashlib
from datetime import date,timedelta
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field

def init(connect):
    with connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS estimates(id TEXT PRIMARY KEY,owner TEXT NOT NULL,customer TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL,created TEXT NOT NULL,updated TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS estimate_events(id INTEGER PRIMARY KEY,estimate_id TEXT,actor TEXT,action TEXT,note TEXT,created TEXT);''')
class EstimateInput(BaseModel):
    service_id:str
    customer_id:str
    sites:int=Field(ge=1,le=5)
    readiness:bool
    complex:bool=False
    requested_start:date
    engineers:int=Field(default=1,ge=1,le=4)
    scope:str=Field(min_length=10,max_length=1500)
    equipment:str=Field(min_length=3,max_length=600)
    license:str=Field(min_length=3,max_length=600)
    access:str=Field(min_length=3,max_length=600)
    window:str=Field(min_length=3,max_length=600)
    acceptance:str=Field(min_length=10,max_length=1500)
    notes:str=Field(default='',max_length=1500)
class Transition(BaseModel):action:str;note:str=Field(default='',max_length=1000)

def install(app,connect,user,docs_for,audit):
    router=APIRouter()
    def scope(u,customer):return u['role']=='admin' or customer in u['customers']
    def load(id,u):
        with connect() as c:r=c.execute('SELECT * FROM estimates WHERE id=?',(id,)).fetchone()
        if not r or not scope(u,r['customer']):raise HTTPException(404,'Không có dự toán trong phạm vi được phép.')
        result={**dict(r),'payload':json.loads(r['payload'])}
        allowed={d['id']:d for d in docs_for(u)};result['sources_current']=all(id in allowed for id in result['payload']['source_ids'])
        fingerprint=result['payload'].get('source_fingerprint')
        if fingerprint and result['sources_current']:
            rate=allowed[result['payload']['source_ids'][0]]
            result['sources_current']=hashlib.sha256(json.dumps(rate,sort_keys=True,ensure_ascii=False).encode()).hexdigest()==fingerprint
        return result
    @router.get('/api/estimate/templates')
    def templates(req:Request):
        u=user(req);docs=docs_for(u);customers=[dict(id=d['customer'],name=d['fields']['name']) for d in docs if d['id'].startswith('CRM-')]
        return dict(templates=[dict(id=d['id'],title=d['title'],**d['estimate_template']) for d in docs if d.get('estimate_template')],customers=customers)
    @router.get('/api/estimates')
    def estimates(req:Request):
        u=user(req)
        with connect() as c:rows=c.execute('SELECT id,customer FROM estimates ORDER BY updated DESC LIMIT 200').fetchall()
        return [load(r['id'],u) for r in rows if scope(u,r['customer'])]
    @router.post('/api/estimates')
    def create(data:EstimateInput,req:Request):
        u=user(req);docs=docs_for(u);allowed={d['id']:d for d in docs}
        if not scope(u,data.customer_id) or 'CRM-'+data.customer_id not in allowed:raise HTTPException(403,'Khách hàng không thuộc phạm vi tài khoản.')
        s=next((d['service'] for d in docs if d.get('service',{}).get('id')==data.service_id),None)
        if not s:raise HTTPException(400,'Dịch vụ/định mức không còn được phép sử dụng.')
        effort=s['days']*data.sites;total=s['price']*data.sites
        ready=data.readiness and not data.complex
        # Conservative serial schedule. Engineers do not automatically divide dependent tasks.
        start=data.requested_start
        while start.weekday()>4:start+=timedelta(days=1)
        end=start
        for _ in range(effort-1+2):
            end+=timedelta(days=1)
            while end.weekday()>4:end+=timedelta(days=1)
        payload=dict(inputs=data.model_dump(mode='json'),service=s['name'],unit_price=s['price'],total=total if ready else None,effort=effort if ready else None,reference_total=total,reference_effort=effort,planned_start=start.isoformat() if ready else None,planned_end=end.isoformat() if ready else None,source_ids=[s['source_id'],'CRM-'+data.customer_id],conditions=s['conditions'],note='Chỉ phí công chưa VAT/thiết bị/license. Lịch tuần tự có đệm 2 ngày làm việc, chưa tính nghỉ lễ/chờ; không tự chia effort theo số kỹ sư. PM phải xác nhận nguồn lực.',approved_by=None)
        payload['source_fingerprint']=hashlib.sha256(json.dumps(allowed[s['source_id']],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        id='EST-'+secrets.token_hex(4).upper();stamp=time.strftime('%Y-%m-%d %H:%M:%S');status='draft' if ready else 'needs_survey'
        with connect() as c:
            c.execute('INSERT INTO estimates VALUES(?,?,?,?,?,?,?)',(id,u['id'],data.customer_id,json.dumps(payload,ensure_ascii=False),status,stamp,stamp));c.execute('INSERT INTO estimate_events(estimate_id,actor,action,note,created) VALUES(?,?,?,?,?)',(id,u['username'],'create',status,stamp))
        audit('estimate_create',u['role'],id);return load(id,u)
    @router.post('/api/estimates/{id}/transition')
    def transition(id:str,data:Transition,req:Request):
        u=user(req);item=load(id,u);action=data.action
        if action not in ('submit','approve','reject'):raise HTTPException(400,'Thao tác không hợp lệ.')
        if action=='submit' and u['role']!='admin' and item['owner']!=u['id']:raise HTTPException(403,'Chỉ người tạo hoặc quản trị được gửi duyệt.')
        if action in ('approve','reject') and u['role']!='admin':raise HTTPException(403,'Chỉ quản trị được phê duyệt dự toán demo.')
        if not item['sources_current']:raise HTTPException(409,'Nguồn đã thay đổi hiệu lực; hãy tạo dự toán mới.')
        expected='draft' if action=='submit' else 'submitted'
        if item['status']!=expected:raise HTTPException(409,'Trạng thái hiện tại không cho phép thao tác này.')
        if action in ('approve','reject') and len(data.note.strip())<5:raise HTTPException(400,'Cần ghi lý do hoặc điều kiện duyệt ít nhất 5 ký tự.')
        status={'submit':'submitted','approve':'approved','reject':'rejected'}[action];payload=item['payload'];stamp=time.strftime('%Y-%m-%d %H:%M:%S')
        if action=='approve':payload['approved_by']=u['username'];payload['approval_note']=data.note
        with connect() as c:
            cur=c.execute('UPDATE estimates SET status=?,payload=?,updated=? WHERE id=? AND status=?',(status,json.dumps(payload,ensure_ascii=False),stamp,id,expected))
            if cur.rowcount!=1:raise HTTPException(409,'Dự toán đã được cập nhật ở phiên khác.')
            c.execute('INSERT INTO estimate_events(estimate_id,actor,action,note,created) VALUES(?,?,?,?,?)',(id,u['username'],action,data.note,stamp))
        audit('estimate_'+action,u['role'],id);return load(id,u)
    @router.get('/api/estimates/{id}/events')
    def events(id:str,req:Request):
        load(id,user(req))
        with connect() as c:return [dict(r) for r in c.execute('SELECT actor,action,note,created FROM estimate_events WHERE estimate_id=? ORDER BY id',(id,))]
    app.include_router(router)
