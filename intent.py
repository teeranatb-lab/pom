"""Origin-boundary policy references and append-only operational intent locks.

Core 0 is NOT represented as executable state or an AI-accessible store.
The immutable policy *reference* is an external artifact's fingerprint, not its content.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


class IntentLedger:
    """User/operational intent changes create revisions; latest proof prevents stale actions."""
    def __init__(self, db_path, audit=None):
        self.db_path = str(db_path)
        self.audit = audit
        with self._db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS runtime_policy_refs (
               policy_id TEXT PRIMARY KEY, declaration_ref TEXT NOT NULL,
               declaration_digest TEXT NOT NULL, five_axes_ref TEXT NOT NULL,
               access_policy_version TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS intent_events (
               seq INTEGER PRIMARY KEY AUTOINCREMENT,
               intent_id TEXT NOT NULL, revision INTEGER NOT NULL,
               actor TEXT NOT NULL, origin_ref TEXT NOT NULL,
               task_type TEXT NOT NULL CHECK(task_type IN ('CHAT','WORK')),
               statement TEXT NOT NULL, constraints_json TEXT NOT NULL,
               parent_hash TEXT, intent_hash TEXT NOT NULL,
               reason TEXT NOT NULL, created_at TEXT NOT NULL,
               UNIQUE(intent_id,revision));
            CREATE TABLE IF NOT EXISTS root_reentries (
               id TEXT PRIMARY KEY, intent_id TEXT, revision INTEGER,
               trigger TEXT NOT NULL, findings TEXT NOT NULL,
               status TEXT NOT NULL DEFAULT 'PENDING', created_at TEXT NOT NULL);
            ''')

    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    def register_policy_ref(self, policy_id, declaration_ref, declaration_digest, five_axes_ref, access_policy_version):
        """Stores external metadata only. Existing policy references cannot be overwritten."""
        if not all([policy_id, declaration_ref, declaration_digest, five_axes_ref, access_policy_version]):
            raise ValueError('all policy reference fields required')
        if len(declaration_digest)!=64 or any(c not in '0123456789abcdef' for c in declaration_digest.lower()):
            raise ValueError('declaration_digest must be sha256 hex')
        with self._db() as db:
            db.execute('INSERT INTO runtime_policy_refs VALUES(?,?,?,?,?,?)',
                       (policy_id,declaration_ref,declaration_digest.lower(),five_axes_ref,access_policy_version,now()))
        return {'status':'REGISTERED_REFERENCE_ONLY','policy_id':policy_id}

    def refuse_core0_operation(self, actor, operation):
        if self.audit:
            self.audit.append(str(uuid.uuid4()),'CORE0_BOUNDARY_DENY',
                              {'actor':actor,'operation':str(operation)[:120],'policy':'no_tool_or_agent_access'})
        return {'status':'DENIED','reason':'Core 0 is conceptual; no read, inspect or write API'}

    def create(self, actor, origin_ref, statement, constraints=None, task_type='CHAT', intent_id=None):
        if not all((actor, origin_ref, statement.strip())):
            raise ValueError('actor, origin_ref and nonempty statement required')
        if task_type not in ('CHAT','WORK'):
            raise ValueError('task_type must be CHAT or WORK')
        intent_id = intent_id or str(uuid.uuid4())
        constraints=constraints or {}
        if not isinstance(constraints, dict):
            raise TypeError('constraints must be a dict')
        base={'id':intent_id,'revision':1,'actor':actor,'origin_ref':origin_ref,
              'task_type':task_type,'statement':statement,'constraints':constraints,'parent_hash':None}
        h=digest(base)
        with self._db() as db:
            db.execute('''INSERT INTO intent_events(intent_id,revision,actor,origin_ref,task_type,
                       statement,constraints_json,parent_hash,intent_hash,reason,created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                       (intent_id,1,actor,origin_ref,task_type,statement,
                        json.dumps(constraints,ensure_ascii=False,sort_keys=True),None,h,'initial',now()))
        if self.audit:self.audit.append(intent_id,'INTENT_LOCK',{'revision':1,'intent_hash':h})
        return {'status':'LOCKED','intent_id':intent_id,'revision':1,'intent_hash':h}

    def latest(self,intent_id):
        with self._db() as db:
            row=db.execute('''SELECT * FROM intent_events WHERE intent_id=? ORDER BY revision DESC LIMIT 1''',(intent_id,)).fetchone()
        if not row:return None
        result=dict(row)
        result['constraints']=json.loads(result.pop('constraints_json'))
        return result

    def revise(self,intent_id,statement=None,constraints_delta=None,reason='',expected_hash=None,actor=None):
        if not reason or not expected_hash or not actor:
            raise ValueError('reason, expected_hash and actor required for delta')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('''SELECT * FROM intent_events WHERE intent_id=? ORDER BY revision DESC LIMIT 1''',(intent_id,)).fetchone()
            if row is None:raise KeyError(intent_id)
            old=dict(row)
            if old['intent_hash']!=expected_hash:raise ValueError('STALE_INTENT_ROOT_REENTRY_REQUIRED')
            if old['actor']!=actor:raise PermissionError('actor_mismatch')
            cons=json.loads(old['constraints_json'])
            if constraints_delta is not None:
                if not isinstance(constraints_delta,dict):raise TypeError('constraints_delta must be dict')
                if any(v is None for v in constraints_delta.values()):
                    raise ValueError('silent_delete_prohibited; omission is not deletion')
                cons.update(constraints_delta)
            new_statement=statement if statement is not None else old['statement']
            if not new_statement.strip():raise ValueError('intent must not be empty')
            rev=old['revision']+1
            base={'id':intent_id,'revision':rev,'actor':old['actor'],'origin_ref':old['origin_ref'],
                  'task_type':old['task_type'],'statement':new_statement,
                  'constraints':cons,'parent_hash':old['intent_hash']}
            h=digest(base)
            db.execute('''INSERT INTO intent_events(intent_id,revision,actor,origin_ref,task_type,
                    statement,constraints_json,parent_hash,intent_hash,reason,created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                    (intent_id,rev,old['actor'],old['origin_ref'],old['task_type'],new_statement,
                     json.dumps(cons,ensure_ascii=False,sort_keys=True),old['intent_hash'],h,reason,now()))
        if self.audit:self.audit.append(intent_id,'INTENT_DELTA',{'revision':rev,'intent_hash':h,'parent_hash':old['intent_hash'],'reason':reason})
        return {'status':'LOCKED','intent_id':intent_id,'revision':rev,'intent_hash':h}

    def proof(self,intent_id,expected_hash):
        current=self.latest(intent_id)
        if current is None:return {'status':'FAIL','reason':'intent_not_found'}
        matches=current['intent_hash']==expected_hash
        if not matches:
            self.reenter(intent_id, current['revision'],'latest_intent_mismatch',{'expected_hash':expected_hash,'actual_hash':current['intent_hash']})
        return {'status':'PASS' if matches else 'ROOT_REENTRY','latest_revision':current['revision'],
                'intent_hash':current['intent_hash'],'reason':None if matches else 'stale_intent'}

    def reenter(self,intent_id,revision,trigger,findings):
        id_=str(uuid.uuid4())
        with self._db() as db:
            db.execute('INSERT INTO root_reentries VALUES(?,?,?,?,?,?,?)',
                       (id_,intent_id,revision,trigger,json.dumps(findings,ensure_ascii=False), 'PENDING',now()))
        if self.audit:self.audit.append(intent_id or id_,'ROOT_REENTRY',{'trigger':trigger,'ref':id_})
        return {'status':'ROOT_REENTRY','reentry_id':id_,'trigger':trigger}
