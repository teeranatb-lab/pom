"""Local sandbox allowlist gate. NOT production authentication or policy engine."""
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta


class CANTI:
    ALLOWED = {'read', 'reason', 'recommend', 'sandbox_write', 'sandbox_train', 'anchor', 'source_apply', 'computer_view', 'computer_control', 'plugin_read', 'plugin_invoke', 'space_read', 'space_write', 'skill_read', 'skill_run', 'notify_email'}

    def __init__(self, db_path):
        self.db_path = str(db_path)
        with self._conn() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS permissions (
                grant_id TEXT PRIMARY KEY, action_scope TEXT NOT NULL,
                resource TEXT NOT NULL, granted_by TEXT NOT NULL,
                granted_at TEXT NOT NULL, expires_at TEXT, revoked_at TEXT)''')

    def _conn(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def grant(self, scope, resource, granted_by, ttl=None):
        if scope not in self.ALLOWED:
            return {'status':'REJECTED','reason':f'scope_not_allowed:{scope}'}
        if not resource or not granted_by:
            return {'status':'REJECTED','reason':'resource_and_granter_required'}
        if ttl is not None and ttl <= 0:
            return {'status':'REJECTED','reason':'ttl_must_be_positive'}
        gid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expiry = (now+timedelta(seconds=ttl)).isoformat() if ttl else None
        with self._conn() as db:
            db.execute('INSERT INTO permissions VALUES(?,?,?,?,?,?,NULL)',
                       (gid,scope,resource,granted_by,now.isoformat(),expiry))
        return {'status':'GRANTED','grant_id':gid,'warning':'local_development_grant_only'}

    def revoke(self, grant_id):
        with self._conn() as db:
            cur = db.execute('UPDATE permissions SET revoked_at=? WHERE grant_id=? AND revoked_at IS NULL',
                             (datetime.now(timezone.utc).isoformat(), grant_id))
        return {'status':'REVOKED' if cur.rowcount else 'NOT_FOUND'}

    def check(self, scope, resource):
        if scope not in self.ALLOWED:
            return {'allowed':False,'reason':f'scope_not_allowed:{scope}'}
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as db:
            row = db.execute('''SELECT grant_id FROM permissions WHERE action_scope=?
                AND resource=? AND revoked_at IS NULL AND
                (expires_at IS NULL OR expires_at>?) ORDER BY granted_at DESC LIMIT 1''',
                (scope,resource,now)).fetchone()
        return {'allowed':bool(row),'grant_id':row[0] if row else None}
