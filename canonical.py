"""Immutable external canonical references and explicitly authorized append/inherit/delta ledger.

No code path edits the master PDF, Origin's declaration or Archive.
"""
import json
import sqlite3
import uuid
from .intent import digest,now


class CanonicalLedger:
    def __init__(self, db_path, audit=None):
        self.db_path=str(db_path);self.audit=audit
        with self._db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS canonical_events (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, change_id TEXT UNIQUE NOT NULL,
              parent_hash TEXT, state_hash TEXT NOT NULL,
              state_json TEXT NOT NULL, delta_json TEXT NOT NULL,
              reason TEXT NOT NULL, source_refs TEXT NOT NULL,
              requested_by TEXT NOT NULL, approved_by TEXT NOT NULL,
              expected_tests TEXT NOT NULL, affected_layers TEXT NOT NULL,
              risk_assessment TEXT NOT NULL, created_at TEXT NOT NULL);
            ''')

    def _db(self):
        db=sqlite3.connect(self.db_path,timeout=15);db.row_factory=sqlite3.Row;return db

    def current(self):
        with self._db() as db:
            row=db.execute('SELECT * FROM canonical_events ORDER BY seq DESC LIMIT 1').fetchone()
        return dict(row) if row else None

    def initialize(self,master_ref,master_sha256,actor):
        if not master_ref or not actor or len(master_sha256)!=64:raise ValueError('master ref, sha256 and actor required')
        state={'master_ref':master_ref,'master_sha256':master_sha256,
               'invariants':['CORE0_CONCEPTUAL','ORIGIN_SOVEREIGN','NO_SILENT_DELETE',
                             'MEANING_SPACE_PERSISTS','LATEST_INTENT_PROOF','PROVENANCE_REQUIRED']}
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM canonical_events LIMIT 1').fetchone():
                raise ValueError('already_initialized')
            h=digest(state)
            db.execute('''INSERT INTO canonical_events(change_id,parent_hash,state_hash,state_json,
              delta_json,reason,source_refs,requested_by,approved_by,expected_tests,affected_layers,
              risk_assessment,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
              (str(uuid.uuid4()),None,h,json.dumps(state,sort_keys=True),json.dumps(state,sort_keys=True),
               'initialize_reference_only',json.dumps([master_ref]),actor,actor,json.dumps([]),
               json.dumps(['canonical']), 'no_mutation_of_master_file',now()))
        return {'status':'REFERENCE_INITIALIZED','state_hash':h}

    def propose_and_apply(self,change_id,parent_hash,delta,reason,source_refs,requester,approver,
                          affected_layers,expected_tests,risk_assessment):
        if not all([change_id,parent_hash,delta,reason,source_refs,requester,approver,affected_layers,
                    expected_tests,risk_assessment]):
            raise ValueError('complete authorized ChangeRequest required')
        if requester!=approver: # By design this is local Origin-only approval proof (not identity verification)
            raise PermissionError('origin_approval_required; proof_of_identity_external')
        if not isinstance(delta,dict) or any(v is None for v in delta.values()):
            raise ValueError('explicit non-deleting delta required')
        protected={'master_ref','master_sha256','invariants'}
        if protected & delta.keys():raise PermissionError('protected_baseline_must_not_be_overwritten')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            r=db.execute('SELECT state_hash,state_json FROM canonical_events ORDER BY seq DESC LIMIT 1').fetchone()
            if not r:raise ValueError('canonical_not_initialized')
            if r['state_hash']!=parent_hash:raise ValueError('canonical_parent_mismatch')
            state=json.loads(r['state_json'])
            for key,value in delta.items():
                if key in state:raise ValueError('no_overwrite; use a new versioned key')
                state[key]=value
            h=digest(state)
            db.execute('''INSERT INTO canonical_events(change_id,parent_hash,state_hash,state_json,
               delta_json,reason,source_refs,requested_by,approved_by,expected_tests,affected_layers,
               risk_assessment,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
               (change_id,parent_hash,h,json.dumps(state,ensure_ascii=False,sort_keys=True),
                json.dumps(delta,ensure_ascii=False,sort_keys=True),reason,json.dumps(source_refs),
                requester,approver,json.dumps(expected_tests),json.dumps(affected_layers),
                str(risk_assessment),now()))
        if self.audit:self.audit.append(change_id,'CANONICAL_APPEND_DELTA',{'parent_hash':parent_hash,'state_hash':h})
        return {'status':'APPENDED_WITH_INHERITANCE','state_hash':h,'parent_hash':parent_hash}

    def verify(self):
        with self._db() as db:
            rows=db.execute('SELECT * FROM canonical_events ORDER BY seq').fetchall()
        if not rows:return {'status':'NOT_INITIALIZED','versions':0}
        prev=None
        inherited={}
        for row in rows:
            r=dict(row);state=json.loads(r['state_json']);delta=json.loads(r['delta_json'])
            if r['parent_hash']!=prev:return {'status':'FAIL','reason':'parent_mismatch','seq':r['seq']}
            if digest(state)!=r['state_hash']:return {'status':'FAIL','reason':'state_hash_mismatch','seq':r['seq']}
            if prev is not None:
                if any(k not in state or state[k]!=v for k,v in inherited.items()):
                    return {'status':'FAIL','reason':'inheritance_violation','seq':r['seq']}
                if any(k in inherited or state.get(k)!=v for k,v in delta.items()):
                    return {'status':'FAIL','reason':'delta_violation','seq':r['seq']}
            inherited=state;prev=r['state_hash']
        return {'status':'PASS','versions':len(rows),'head_hash':prev}
