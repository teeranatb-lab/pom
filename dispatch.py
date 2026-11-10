"""Ontology-based tool target discovery, without phrase matching or automatic execution.

No actual GIS/CAD tool actions happen here. Candidates are subject to CANTI,
intent/version, evidence, decision and human-approval gates before execution.
"""
import json
import sqlite3
import uuid
from .intent import now


class SemanticActionDispatcher:
    def __init__(self,meaning_space,semantic,audit=None):
        self.ms=meaning_space;self.semantic=semantic;self.audit=audit
        with self._db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS action_capabilities (
                capability_id TEXT PRIMARY KEY, action_cid TEXT NOT NULL,
                action_name TEXT NOT NULL, target_cid TEXT NOT NULL,
                resource_scope TEXT NOT NULL, contract_json TEXT NOT NULL,
                registered_by TEXT NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(action_cid,action_name,target_cid));
            ''')

    def _db(self):
        db=sqlite3.connect(self.ms.db_path,timeout=15);db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON');return db

    def register_capability(self,action_cid,action_name,target_cid,resource_scope,contract,registered_by):
        if not self.ms.get_core(action_cid) or not self.ms.get_core(target_cid):
            raise ValueError('capability requires existing meaning cores')
        if not all([action_name,resource_scope,registered_by]) or not isinstance(contract,dict):
            raise ValueError('action name, scope, contract and registrar required')
        cid=str(uuid.uuid4())
        with self._db() as db:
            db.execute('INSERT INTO action_capabilities VALUES(?,?,?,?,?,?,?,?)',
                       (cid,action_cid,action_name,target_cid,resource_scope,
                        json.dumps(contract,ensure_ascii=False,sort_keys=True),registered_by,now()))
        return {'status':'REGISTERED_ONLY','capability_id':cid}

    def candidates(self,observed_cids,max_hops=4):
        with self._db() as db:
            actions=[dict(x) for x in db.execute('SELECT * FROM action_capabilities ORDER BY capability_id')]
        paths=[]
        for action in actions:
            found=[]
            for seed in observed_cids:
                p=self.semantic.candidate_paths(seed,action['action_cid'],max_hops=max_hops)
                for candidate in p['candidate_paths']:
                    found.append({'source_cid':seed,'path':candidate})
            if found:
                verified=any(p['path']['status']=='CHECKED_GRAPH_PATH' for p in found)
                paths.append({'action_name':action['action_name'],'target_cid':action['target_cid'],
                              'capability_id':action['capability_id'],'contract':json.loads(action['contract_json']),
                              'candidate_paths':found[:20],
                              'status':'REVIEW_ELIGIBLE_NOT_APPROVED' if verified else 'CANDIDATE_NOT_VERIFIED',
                              'auto_execute':False})
        return {'status':'CANDIDATES','actions':paths,
                'warning':'Graph matching is not proof that a user authorized an action'}
