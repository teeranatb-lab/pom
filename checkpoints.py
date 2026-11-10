"""Finite stage contracts and signed audit-linked checkpoint receipts."""
from __future__ import annotations
import hashlib
import hmac
import json
import sqlite3
import uuid
from .intent import now,digest

STAGES=('F-00','F-01','F-02','F-03','F-04','X-00',
        'OP-01','OP-02','OP-03','OP-04','OP-05','OP-06','OP-07','OP-08','OP-09','OP-10')
STAGE_PURPOSE={
 'F-00':'Core 0 trust-boundary reference only',
 'F-01':'Origin identity and permission-reference contract',
 'F-02':'Origin intent external immutable declaration ref',
 'F-03':'Five ethical axes risk assessment',
 'F-04':'Current user intent',
 'X-00':'Shared Meaning Space context',
 'OP-01':'Operational intent locked',
 'OP-02':'Canonical state inherited',
 'OP-03':'Evidence/assumption typing and registered sources',
 'OP-04':'Reasoning, resonance, alternatives and root-reentry',
 'OP-05':'Latest-intent proof',
 'OP-06':'Verified decision/quality gate',
 'OP-07':'CANTI contract and action',
 'OP-08':'Effects independently observed',
 'OP-09':'Outcome, provenance and hash chain',
 'OP-10':'Return compare with intent and closure'}
STATUS={'PASS','FAIL','PENDING','NOT_TESTED','BLOCKED','SKIPPED','INSUFFICIENT','REVIEW_REQUIRED'}


class Checkpoints:
    def __init__(self,db_path,audit,signing_key=None):
        self.db_path=str(db_path);self.audit=audit
        self.signing_key=signing_key.encode() if isinstance(signing_key,str) else signing_key
        with self._db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS checkpoints (
              checkpoint_id TEXT PRIMARY KEY, trace_id TEXT NOT NULL,
              stage TEXT NOT NULL, status TEXT NOT NULL,
              input_refs TEXT NOT NULL, findings TEXT NOT NULL,
              verifier TEXT NOT NULL, verifier_version TEXT NOT NULL,
              entered_at TEXT NOT NULL,exited_at TEXT NOT NULL,
              authorizer_ref TEXT, failure_ref TEXT, reentry_ref TEXT,
              audit_seq INTEGER NOT NULL,audit_hash TEXT NOT NULL,
              receipt_hash TEXT NOT NULL,signature TEXT);
            ''')

    def _db(self):
        db=sqlite3.connect(self.db_path,timeout=15);db.row_factory=sqlite3.Row;return db

    def record(self,trace_id,stage,status,input_refs,findings,
               verifier='olgm.runtime',verifier_version='0.5.0',
               authorizer_ref=None,failure_ref=None,reentry_ref=None,entered_at=None):
        if stage not in STAGES or status not in STATUS:raise ValueError('bad stage or status')
        if not isinstance(input_refs,(dict,list)) or not isinstance(findings,dict):
            raise ValueError('input refs and findings must be structured')
        entered_at=entered_at or now();exited_at=now();cid=str(uuid.uuid4())
        receipt={'checkpoint_id':cid,'trace_id':trace_id,'stage':stage,'status':status,
                 'input_refs':input_refs,'findings':findings,
                 'verifier':verifier,'verifier_version':verifier_version,
                 'entered_at':entered_at,'exited_at':exited_at,
                 'authorizer_ref':authorizer_ref,'failure_ref':failure_ref,'reentry_ref':reentry_ref}
        seq,chain_hash=self.audit.append(trace_id,'CHECKPOINT',receipt)
        receipt.update({'audit_seq':seq,'audit_hash':chain_hash})
        h=digest(receipt)
        sig=hmac.new(self.signing_key,h.encode(),'sha256').hexdigest() if self.signing_key else None
        with self._db() as db:
            db.execute('''INSERT INTO checkpoints VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                       (cid,trace_id,stage,status,json.dumps(input_refs,ensure_ascii=False,sort_keys=True),
                        json.dumps(findings,ensure_ascii=False,sort_keys=True),verifier,verifier_version,
                        entered_at,exited_at,authorizer_ref,failure_ref,reentry_ref,seq,chain_hash,h,sig))
        return {'checkpoint_id':cid,'stage':stage,'status':status,'audit_seq':seq,
                'audit_hash':chain_hash,'receipt_hash':h,'signed':bool(sig)}

    def for_trace(self,trace_id):
        with self._db() as db:
            rows=db.execute('SELECT * FROM checkpoints WHERE trace_id=? ORDER BY audit_seq',(trace_id,)).fetchall()
        return [dict(x) for x in rows]

    def verify(self,trace_id=None):
        chain_ok,chain_detail=self.audit.verify()
        if not chain_ok:return {'status':'FAIL','reason':f'audit_chain:{chain_detail}'}
        with self._db() as db:
            rows=db.execute('SELECT * FROM checkpoints '+('WHERE trace_id=? ' if trace_id else '')+'ORDER BY audit_seq',
                            (trace_id,) if trace_id else ()).fetchall()
            audits=dict(db.execute('SELECT seq,self_hash FROM audit_chain'))
        for row in rows:
            r=dict(row)
            base={'checkpoint_id':r['checkpoint_id'],'trace_id':r['trace_id'],'stage':r['stage'],
                  'status':r['status'],'input_refs':json.loads(r['input_refs']),
                  'findings':json.loads(r['findings']),'verifier':r['verifier'],
                  'verifier_version':r['verifier_version'],'entered_at':r['entered_at'],
                  'exited_at':r['exited_at'],'authorizer_ref':r['authorizer_ref'],
                  'failure_ref':r['failure_ref'],'reentry_ref':r['reentry_ref'],
                  'audit_seq':r['audit_seq'],'audit_hash':r['audit_hash']}
            h=digest(base)
            if h!=r['receipt_hash'] or audits.get(r['audit_seq'])!=r['audit_hash']:
                return {'status':'FAIL','checkpoint_id':r['checkpoint_id'],'reason':'receipt_or_audit_mismatch'}
            if self.signing_key:
                expected=hmac.new(self.signing_key,h.encode(),'sha256').hexdigest()
                if not r['signature'] or not hmac.compare_digest(expected,r['signature']):
                    return {'status':'FAIL','checkpoint_id':r['checkpoint_id'],'reason':'signature_mismatch'}
        return {'status':'PASS','count':len(rows),'signed_with_key':bool(self.signing_key)}
