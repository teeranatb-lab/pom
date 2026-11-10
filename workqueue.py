"""Persistent finite-step worker for on-demand or externally scheduled AI observation.
No worker auto-starts on import; every step requires permissions and latest intent.
"""
import json
import sqlite3
import time
import uuid
from .intent import now


class AgentQueue:
    def __init__(self,runtime):
        self.rt=runtime;self.db_path=runtime.ms.db_path
        with self._db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS agent_jobs (
                    job_id TEXT PRIMARY KEY,intent_id TEXT NOT NULL,
                    intent_hash TEXT NOT NULL,intent_tag TEXT NOT NULL,
                    status TEXT NOT NULL, result_json TEXT,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            ''')

    def _db(self):
        db=sqlite3.connect(self.db_path,timeout=15);db.row_factory=sqlite3.Row;return db

    def enqueue(self,intent_id,intent_hash,intent_tag='why'):
        if not self.rt.canti.check('reason','agent.ask')['allowed']:
            return {'status':'DENIED','reason':'CANTI_reason_grant_required'}
        if self.rt.intent.proof(intent_id,intent_hash)['status']!='PASS':
            return {'status':'ROOT_REENTRY','reason':'stale_intent'}
        job_id=str(uuid.uuid4())
        with self._db() as db:
            db.execute('INSERT INTO agent_jobs VALUES(?,?,?,?,?,?,?,?)',
                       (job_id,intent_id,intent_hash,intent_tag,'QUEUED',None,now(),now()))
        self.rt.audit.append(job_id,'JOB_QUEUED',{'intent_id':intent_id,'intent_hash':intent_hash})
        return {'status':'QUEUED','job_id':job_id}

    def step(self):
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute("SELECT * FROM agent_jobs WHERE status='QUEUED' ORDER BY created_at,job_id LIMIT 1").fetchone()
            if not row:return {'status':'IDLE'}
            job=dict(row)
            db.execute("UPDATE agent_jobs SET status='RUNNING',updated_at=? WHERE job_id=?",(now(),job['job_id']))
        intent=self.rt.intent.latest(job['intent_id'])
        if intent is None or intent['intent_hash']!=job['intent_hash']:
            result={'status':'ROOT_REENTRY','reason':'latest_intent_changed'}
        elif self.rt.agent.observer.model.name=='disabled':
            result={'status':'BLOCKED_MODEL','reason':'configured model required for observer'}
        else:
            try:
                result=self.rt.process(intent['statement'],actor=intent['actor'],origin_ref=intent['origin_ref'],
                                       intent_tag=job['intent_tag'],task_type=intent['task_type'],
                                       intent_id=job['intent_id'],expected_intent_hash=job['intent_hash'],
                                       enable_model=True)
            except Exception as exc:
                result={'status':'FAILED','reason':str(exc)[:300]}
        status=('COMPLETED' if result['status'] in ('CANDIDATE','DETERMINISTIC_RESULT','INSUFFICIENT')
                else 'BLOCKED' if result['status'] in ('ROOT_REENTRY','BLOCKED_MODEL','DENIED') else 'FAILED')
        with self._db() as db:
            db.execute('UPDATE agent_jobs SET status=?,result_json=?,updated_at=? WHERE job_id=?',
                       (status,json.dumps(result,ensure_ascii=False),now(),job['job_id']))
        self.rt.audit.append(job['job_id'],'JOB_RESULT',{'status':status,'result_status':result['status']})
        return {'status':status,'job_id':job['job_id'],'result_status':result['status'],
                'trace_id':result.get('trace_id')}

    def run_steps(self,limit=10):
        limit=min(max(int(limit),0),100)
        results=[]
        for _ in range(limit):
            r=self.step()
            if r['status']=='IDLE':break
            results.append(r)
        return {'status':'BATCH_PROCESSED','count':len(results),'jobs':results}
