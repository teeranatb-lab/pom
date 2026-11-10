"""Experience records contain pointers; missing pointers fail closed on rehydration."""
import json
import sqlite3
import uuid
from datetime import datetime, timezone


class EpisodicMemory:
    def __init__(self, db_path, meaning_space):
        self.db_path, self.ms = str(db_path), meaning_space
        with self._conn() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS episodes (
                episode_id TEXT PRIMARY KEY, trace_id TEXT NOT NULL, intent TEXT NOT NULL,
                start_cid TEXT NOT NULL, goal_cid TEXT NOT NULL,
                ordered_relation_ids TEXT NOT NULL,
                outcome TEXT NOT NULL CHECK(outcome IN ('success','failure','unresolved')),
                evidence_ref TEXT, owner TEXT, schema_version TEXT NOT NULL,
                created_at TEXT NOT NULL)''')

    def _conn(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def record(self, trace_id, intent, start_cid, goal_cid, relation_ids, outcome,
               evidence_ref=None, owner=None):
        if outcome not in ('success','failure','unresolved'):
            return {'status':'REJECTED','reason':'invalid_outcome'}
        if not self.ms.get_core(start_cid) or not self.ms.get_core(goal_cid):
            return {'status':'REJECTED','reason':'missing_core_pointer'}
        if any(self.ms.get_edge(eid) is None for eid in relation_ids):
            return {'status':'REJECTED','reason':'missing_relation_pointer'}
        if outcome == 'success' and (not evidence_ref or not self.ms.get_evidence(evidence_ref)):
            return {'status':'REJECTED','reason':'success_requires_registered_evidence'}
        eid = str(uuid.uuid4())
        with self._conn() as db:
            db.execute('INSERT INTO episodes VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (eid,trace_id,intent,start_cid,goal_cid,json.dumps(relation_ids),
                        outcome,evidence_ref,owner,'v1',datetime.now(timezone.utc).isoformat()))
        return {'status':'RECORDED','episode_id':eid}

    def rehydrate(self, episode_id):
        with self._conn() as db:
            row = db.execute('SELECT trace_id,intent,start_cid,goal_cid,ordered_relation_ids,outcome,evidence_ref FROM episodes WHERE episode_id=?',
                             (episode_id,)).fetchone()
        if not row:
            return {'status':'NOT_FOUND'}
        tid,intent,start,goal,rjson,outcome,eref = row
        start_obj,goal_obj = self.ms.get_core(start),self.ms.get_core(goal)
        relations = [self.ms.get_edge(r) for r in json.loads(rjson)]
        if not start_obj or not goal_obj or any(r is None for r in relations):
            return {'status':'INCOMPLETE','reason':'dangling_pointers'}
        return {'status':'REHYDRATED','trace_id':tid,'intent':intent,'outcome':outcome,
                'evidence_ref':eref,'start':start_obj,'goal':goal_obj,'relations':relations}
