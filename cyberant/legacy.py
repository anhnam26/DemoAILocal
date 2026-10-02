"""Legacy schema upgrade, used ONLY on private staging snapshots by operations."""
from cyberant import accounts, conversations, quality_feedback, token_usage


def upgrade(connect):
    with connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS docs(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,profile TEXT,created REAL);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,ts TEXT,action TEXT,role TEXT,detail TEXT);
        CREATE TABLE IF NOT EXISTS chats(id INTEGER PRIMARY KEY,session TEXT,question TEXT,result TEXT,ts TEXT);
        CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY,chat_id INTEGER,session TEXT,rating INTEGER,ts TEXT);''')
        if 'context_after' not in {r[1] for r in c.execute('PRAGMA table_info(sessions)')}:
            c.execute('ALTER TABLE sessions ADD COLUMN context_after INTEGER DEFAULT 0')
        if 'user_id' not in {r[1] for r in c.execute('PRAGMA table_info(chats)')}:
            c.execute('ALTER TABLE chats ADD COLUMN user_id TEXT')
    accounts.init(connect)
    # Resolve historical chat owners BEFORE importing old token usage.
    conversations.init(connect)
    token_usage.init(connect)
    quality_feedback.init(connect)
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS source_sync(id TEXT PRIMARY KEY,digest TEXT NOT NULL)')