"""CANTI seven-stage action in a constrained LOCAL SANDBOX only.

No OS commands, network requests, arbitrary filenames, DB alterations or outside tools.
Separate approval and current intent proof are required. Idempotency is persistent.
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from .intent import now,digest


class ActionController:
    ACTIONS={'sandbox.note','sandbox.counter'}
    def __init__(self, db_path, canti, intents, checkpoints, audit, signatures=None):
        self.db_path=str(db_path);self.canti=canti;self.intents=intents;self.checkpoints=checkpoints;self.audit=audit
        self.signatures=signatures
        with self._db() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS action_plans (
                plan_id TEXT PRIMARY KEY, intent_id TEXT NOT NULL,
                intent_hash TEXT NOT NULL, action_name TEXT NOT NULL, resource TEXT NOT NULL,
                args_json TEXT NOT NULL, request_hash TEXT NOT NULL,
                status TEXT NOT NULL, requested_by TEXT NOT NULL,
                approved_by TEXT, approval_ref TEXT, created_at TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS sandbox_outcomes (
                request_hash TEXT PRIMARY KEY, plan_id TEXT NOT NULL,
                outcome_json TEXT NOT NULL, observed_at TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS sandbox_notes (
                note_id TEXT PRIMARY KEY, text TEXT NOT NULL, plan_id TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS sandbox_counters (
                name TEXT PRIMARY KEY, count INTEGER NOT NULL);
            ''')

    def _db(self):
        db=sqlite3.connect(self.db_path,timeout=15);db.row_factory=sqlite3.Row;return db

    def propose(self,intent_id,intent_hash,action_name,resource,args,requested_by,idempotency_key):
        if action_name not in self.ACTIONS:
            return {'status':'DENIED','reason':'action_not_in_sandbox_allowlist'}
        if resource != action_name or not isinstance(args,dict):
            return {'status':'DENIED','reason':'exact_resource_and_structured_args_required'}
        if not idempotency_key or not requested_by:return {'status':'DENIED','reason':'idempotency_and_identity_required'}
        if self.intents.proof(intent_id,intent_hash)['status']!='PASS':
            return {'status':'ROOT_REENTRY','reason':'stale_intent'}
        if action_name=='sandbox.note' and (not isinstance(args.get('text'),str) or len(args['text'])>3000):
            return {'status':'DENIED','reason':'invalid_note'}
        if action_name=='sandbox.counter' and (not isinstance(args.get('name'),str) or
                 not 1<=len(args['name'])<=80 or not args['name'].replace('_','').isalnum()):
            return {'status':'DENIED','reason':'invalid_counter'}
        plan_id=str(uuid.uuid4());request_hash=digest({'intent_id':intent_id,'intent_hash':intent_hash,
            'action':action_name,'resource':resource,'args':args,'idempotency_key':idempotency_key})
        with self._db() as db:
            db.execute('INSERT INTO action_plans VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                       (plan_id,intent_id,intent_hash,action_name,resource,
                        json.dumps(args,ensure_ascii=False,sort_keys=True),request_hash,
                        'PENDING_APPROVAL',requested_by,None,None,now()))
        self.audit.append(plan_id,'ACTION_PROPOSE',{'action':action_name,'intent_hash':intent_hash,'request_hash':request_hash})
        return {'status':'PENDING_APPROVAL','plan_id':plan_id,'request_hash':request_hash}

    def approve(self,plan_id,approved_by,approval_ref,signed_receipt=None,signature_hex=None,require_signature=False):
        import os
        require_signature=require_signature or os.getenv('OLGM_REQUIRE_SIGNED_APPROVAL')=='1'
        if not approved_by or not approval_ref:raise ValueError('explicit approval reference required')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            plan=db.execute('SELECT * FROM action_plans WHERE plan_id=?',(plan_id,)).fetchone()
            if not plan:return {'status':'NOT_FOUND'}
            if plan['status']!='PENDING_APPROVAL':return {'status':'DENIED','reason':'not_pending_approval'}
            latest=db.execute('SELECT intent_hash FROM intent_events WHERE intent_id=? ORDER BY revision DESC LIMIT 1',
                               (plan['intent_id'],)).fetchone()
            if not latest or latest['intent_hash']!=plan['intent_hash']:
                return {'status':'ROOT_REENTRY','reason':'stale_intent'}
            if not self.canti.check('sandbox_write',plan['resource'])['allowed']:
                return {'status':'DENIED','reason':'CANTI_no_grant'}
            if require_signature or signed_receipt is not None:
                if not self.signatures or signed_receipt is None or not signature_hex:
                    return {'status':'DENIED','reason':'signed_approval_required'}
                verified=self.signatures.verify(signed_receipt,signature_hex,
                              expected_plan_id=plan_id,expected_resource=plan['resource'],consume=False)
                if (verified['status']!='VERIFIED_SIGNATURE' or
                    signed_receipt['intent_id']!=plan['intent_id'] or
                    signed_receipt['intent_hash']!=plan['intent_hash'] or
                    signed_receipt['principal']!=approved_by or
                    signed_receipt['approval_ref']!=approval_ref):
                    return {'status':'DENIED','reason':'signature_or_intent_binding_invalid'}
            if signed_receipt is not None:
                try:
                    from olgm.intent import digest
                    db.execute('INSERT INTO signed_auth_consumptions VALUES(?,?,?,?)',
                       (signed_receipt['nonce'],signed_receipt['principal'],digest(signed_receipt),now()))
                except sqlite3.IntegrityError:
                    return {'status':'DENIED','reason':'nonce_replay'}
            db.execute("UPDATE action_plans SET status='APPROVED',approved_by=?,approval_ref=? WHERE plan_id=?",
                       (approved_by,approval_ref,plan_id))
        self.audit.append(plan_id,'ACTION_APPROVE',{'approved_by':approved_by,'approval_ref':approval_ref})
        return {'status':'APPROVED','plan_id':plan_id}

    def execute(self,plan_id,observed_by='local_runtime'):
        """Transactions make repeated calls idempotent; no side effects outside sandbox DB."""
        # Check intent before locking database: a stale-intent reentry logs to same DB.
        with self._db() as db0:
            before=db0.execute('SELECT intent_id,intent_hash FROM action_plans WHERE plan_id=?',(plan_id,)).fetchone()
        if before and self.intents.proof(before['intent_id'],before['intent_hash'])['status']!='PASS':
            return {'status':'ROOT_REENTRY','reason':'stale_intent'}
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            p=db.execute('SELECT * FROM action_plans WHERE plan_id=?',(plan_id,)).fetchone()
            if not p:return {'status':'NOT_FOUND'}
            if p['status'] not in ('APPROVED','EXECUTED'):
                return {'status':'DENIED','reason':'not_approved'}
            existing=db.execute('SELECT outcome_json FROM sandbox_outcomes WHERE request_hash=?',
                                (p['request_hash'],)).fetchone()
            if existing:return {**json.loads(existing['outcome_json']),'idempotent_replay':True}
            latest=db.execute('SELECT intent_hash FROM intent_events WHERE intent_id=? ORDER BY revision DESC LIMIT 1',
                               (p['intent_id'],)).fetchone()
            if not latest or latest['intent_hash']!=p['intent_hash']:
                return {'status':'ROOT_REENTRY','reason':'stale_intent'}
            if not self.canti.check('sandbox_write',p['resource'])['allowed']:
                return {'status':'DENIED','reason':'CANTI_no_grant_or_expired'}
            args=json.loads(p['args_json'])
            if p['action_name']=='sandbox.note':
                nid=str(uuid.uuid4())
                db.execute('INSERT INTO sandbox_notes VALUES(?,?,?)',(nid,args['text'],plan_id))
                effected={'note_id':nid,'recorded':True}
            elif p['action_name']=='sandbox.counter':
                name=args['name']
                db.execute('INSERT INTO sandbox_counters(name,count) VALUES(?,1) ON CONFLICT(name) DO UPDATE SET count=count+1',(name,))
                count=db.execute('SELECT count FROM sandbox_counters WHERE name=?',(name,)).fetchone()[0]
                effected={'counter':name,'count':count}
            else:raise RuntimeError('unrecognized_action')
            result={'status':'EXECUTED_SANDBOX','plan_id':plan_id,'observed_by':observed_by,'effects':effected,
                    'goal_compliance':'NOT_TESTED','outside_side_effects':False}
            db.execute('INSERT INTO sandbox_outcomes VALUES(?,?,?,?)',
                       (p['request_hash'],plan_id,json.dumps(result,ensure_ascii=False),now()))
            db.execute("UPDATE action_plans SET status='EXECUTED' WHERE plan_id=?",(plan_id,))
        for step,details in [
            ('TARGET_LOCK',{'intent_hash':p['intent_hash'],'resource':p['resource']}),
            ('PATH_ANALYSIS',{'action':p['action_name'],'allowlist':True}),
            ('EXECUTE_NO_EXPAND',{'sandbox_only':True,'plan_id':plan_id}),
            ('OBSERVE',{'observer':observed_by,'effects':effected}),
            ('EMPIRICAL_EVAL',{'database_effect':effected,'goal_quality':'NOT_TESTED'}),
            ('REFINE_ONLY_DEVIATIONS',{'refinements':0,'reason':'no_verified_deviation_review'}),
            ('TERMINATE',{'plan_id':plan_id,'result':'EXECUTED_SANDBOX'})]:
            self.audit.append(plan_id,'CANTI_STAGE',{'stage':step,'details':details})
        self.checkpoints.record(plan_id,'OP-07','PASS',{'plan_id':plan_id,'intent_hash':p['intent_hash']},
                                {'execution':'sandbox_only','request_hash':p['request_hash']},authorizer_ref=p['approval_ref'])
        self.checkpoints.record(plan_id,'OP-08','PASS',{'plan_id':plan_id},
                                {'observed_by':observed_by,'effects':effected,'scope':'sandbox_database'},
                                authorizer_ref=p['approval_ref'])
        self.audit.append(plan_id,'CANTI_EFFECT',{'effects':effected,'observed_by':observed_by})
        return result
