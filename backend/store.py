"""SQLite project, versions and experiment persistence. No login: intended for local use."""
import sqlite3
import json
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone

# Vercel's function filesystem is read-only except /tmp. /tmp storage is
# temporary and NOT durable; use an external database for permanent projects.
_default_data_dir = ('/tmp/qubitrail' if (os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'))
                     else str(Path(__file__).resolve().parent.parent / 'data'))
DATA = Path(os.environ.get('QUBITRAIL_DATA_DIR') or _default_data_dir)
DATA.mkdir(parents=True,exist_ok=True)
DB=DATA/'qubitrail.db'

def con():
    conn=sqlite3.connect(DB,timeout=5)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

def init():
    with con() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',circuit TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS versions (id TEXT PRIMARY KEY,project_id TEXT NOT NULL,created_at TEXT NOT NULL,label TEXT NOT NULL,circuit TEXT NOT NULL,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS experiments (id TEXT PRIMARY KEY,project_id TEXT,created_at TEXT NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL,FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL);
        ''')

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')

def list_projects():
    with con() as db:
        return [{**dict(r),'circuit':json.loads(r['circuit'])} for r in db.execute('SELECT * FROM projects ORDER BY updated_at DESC').fetchall()]

def get_project(pid):
    with con() as db:
        r=db.execute('SELECT * FROM projects WHERE id=?',(pid,)).fetchone()
        return {**dict(r),'circuit':json.loads(r['circuit'])} if r else None

def save_project(data,pid=None):
    circuit=data['circuit']; name=str(data.get('name',circuit.get('name','Untitled Circuit')))[:120];description=str(data.get('description',''))[:1000]
    when=now()
    with con() as db:
        if pid:
            old=db.execute('SELECT id FROM projects WHERE id=?',(pid,)).fetchone()
            if not old:return None
            db.execute('UPDATE projects SET name=?,description=?,circuit=?,updated_at=? WHERE id=?',(name,description,json.dumps(circuit),when,pid))
        else:
            pid=str(uuid.uuid4())
            db.execute('INSERT INTO projects VALUES (?,?,?,?,?,?)',(pid,name,description,json.dumps(circuit),when,when))
        db.execute('INSERT INTO versions VALUES (?,?,?,?,?)',(str(uuid.uuid4()),pid,when,'Saved snapshot',json.dumps(circuit)))
        # Preserve most recent 30 versions of each project.
        db.execute('DELETE FROM versions WHERE project_id=? AND id NOT IN (SELECT id FROM versions WHERE project_id=? ORDER BY created_at DESC,rowid DESC LIMIT 30)',(pid,pid))
    return get_project(pid)

def delete_project(pid):
    with con() as db:
        r=db.execute('DELETE FROM projects WHERE id=?',(pid,))
        return r.rowcount>0

def versions(pid):
    with con() as db:
        return [{**dict(r),'circuit':json.loads(r['circuit'])} for r in db.execute('SELECT * FROM versions WHERE project_id=? ORDER BY created_at DESC,rowid DESC',(pid,)).fetchall()]

def add_experiment(kind,payload,project_id=None):
    eid=str(uuid.uuid4());when=now()
    with con() as db:
        if project_id and not db.execute('SELECT 1 FROM projects WHERE id=?',(project_id,)).fetchone():project_id=None
        db.execute('INSERT INTO experiments VALUES (?,?,?,?,?)',(eid,project_id,when,kind,json.dumps(payload,default=str)))
    return {'id':eid,'created_at':when,'kind':kind,'project_id':project_id}

def list_experiments(limit=50):
    with con() as db:
        return [{**dict(r),'payload':json.loads(r['payload'])} for r in db.execute('SELECT * FROM experiments ORDER BY created_at DESC,rowid DESC LIMIT ?',(max(1,min(limit,100)),)).fetchall()]
