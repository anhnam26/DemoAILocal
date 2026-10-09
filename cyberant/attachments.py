"""Owner/conversation-scoped files stored atomically with extracted units."""
import hashlib,json,secrets
from cyberant.document_extractors import evidence_body
from datetime import date
from fastapi import HTTPException

SCHEMA_VERSION=1


def initialize(c):
    c.execute('CREATE TABLE IF NOT EXISTS conversations.attachment_schema(version INTEGER NOT NULL)')
    if not c.execute('SELECT 1 FROM attachment_schema').fetchone():c.execute('INSERT INTO attachment_schema VALUES(?)',(SCHEMA_VERSION,))
    c.execute('''CREATE TABLE IF NOT EXISTS conversations.attachments(
        id TEXT PRIMARY KEY,user_id TEXT NOT NULL,conversation_id TEXT NOT NULL,
        name TEXT NOT NULL,digest TEXT NOT NULL,raw BLOB NOT NULL,extracted TEXT NOT NULL,created TEXT NOT NULL)''')
    c.execute('CREATE INDEX IF NOT EXISTS conversations.attachments_owner ON attachments(user_id,conversation_id)')


def available(c):
    if 'conversations' not in {r[1] for r in c.execute('PRAGMA database_list')}:return False
    if not c.execute("SELECT 1 FROM conversations.sqlite_master WHERE type='table' AND name='attachment_schema'").fetchone():return False
    row=c.execute('SELECT version FROM attachment_schema').fetchone()
    return bool(row and row[0]==SCHEMA_VERSION)


def require(c):
    if not available(c):raise HTTPException(409,'File chat chưa được nâng cấp schema. Quản trị cần chạy operations upgrade-attachments vào thư mục dữ liệu MỚI; không sửa DB đang chạy.')


def owner(c,u,conversation_id):
    if not c.execute('SELECT 1 FROM conversations WHERE id=? AND user_id=?',(conversation_id,u['id'])).fetchone():raise HTTPException(404,'Không tìm thấy cuộc trò chuyện của tài khoản này.')


def save(connect,u,conversation_id,name,raw,extracted,now):
    id='FILE-'+secrets.token_hex(12).upper()
    with connect() as c:
        c.execute('BEGIN IMMEDIATE');require(c);owner(c,u,conversation_id)
        account=c.execute('SELECT active FROM users WHERE id=?',(u['id'],)).fetchone()
        if not account or not account['active']:raise HTTPException(403,'Tài khoản không còn hoạt động.')
        count,size=c.execute('SELECT COUNT(*),COALESCE(SUM(length(raw)+length(CAST(extracted AS BLOB))),0) FROM attachments WHERE user_id=? AND conversation_id=?',(u['id'],conversation_id)).fetchone()
        total=c.execute('SELECT COALESCE(SUM(length(raw)+length(CAST(extracted AS BLOB))),0) FROM attachments WHERE user_id=?',(u['id'],)).fetchone()[0]
        encoded=json.dumps(extracted,ensure_ascii=False);cost=len(raw)+len(encoded.encode('utf8'))
        if count>=10 or size+cost>50_000_000 or total+cost>200_000_000:raise HTTPException(413,'Giới hạn 10 file/50 MB mỗi hội thoại và 200 MB mỗi tài khoản. Xóa file cũ trước khi tải thêm.')
        c.execute('INSERT INTO attachments VALUES(?,?,?,?,?,?,?,?)',(id,u['id'],conversation_id,name,hashlib.sha256(raw).hexdigest(),raw,encoded,now()))
    return id


def listing(connect,u,conversation_id):
    with connect() as c:
        owner(c,u,conversation_id)
        if not available(c):return []
        rows=c.execute('SELECT id,name,digest,length(raw) AS size,extracted,created FROM attachments WHERE user_id=? AND conversation_id=? ORDER BY created,id',(u['id'],conversation_id)).fetchall()
    return [dict(id=r['id'],name=r['name'],digest=r['digest'],size=r['size'],created=r['created'],warnings=json.loads(r['extracted'])['warnings'],units=len(json.loads(r['extracted'])['units'])) for r in rows]


def documents(connect,u,conversation_id):
    with connect() as c:
        owner(c,u,conversation_id)
        if not available(c):return []
        rows=c.execute('SELECT id,name,digest,extracted FROM attachments WHERE user_id=? AND conversation_id=? ORDER BY created,id',(u['id'],conversation_id)).fetchall()
    docs=[]
    for row in rows:
        parsed=json.loads(row['extracted'])
        for i,unit in enumerate(parsed['units'],1):
            body=evidence_body(unit)
            docs.append(dict(id=row['id']+'-'+str(i),attachment_id=row['id'],title=row['name']+' · '+unit['location'],body=body,
                category='File hội thoại',version='extract-'+str(parsed.get('extraction_version',1)),owner='Người tải lên',valid_to='2099-12-31',valid_from=date.today().isoformat(),
                status='approved',review_status='user_provided_unverified',group='F',knowledge_type='theory',
                extraction_structure=unit.get('structure'),extracted_text=unit['body'],
                provenance=dict(file=row['name'],location=unit['location'],file_digest=row['digest']),source_digest=hashlib.sha256(body.encode()).hexdigest()))
    return docs


def delete(connect,u,conversation_id,id):
    with connect() as c:
        c.execute('BEGIN IMMEDIATE');require(c);owner(c,u,conversation_id)
        if not c.execute('DELETE FROM attachments WHERE id=? AND user_id=? AND conversation_id=?',(id,u['id'],conversation_id)).rowcount:raise HTTPException(404,'Không có file thuộc hội thoại này.')