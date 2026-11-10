"""Typed graph traversal, resonance, alternate paths, contradictions, meaning proposals.
Lexical similarity only seeds candidate CIDs, never establishes semantic truth.
"""
from __future__ import annotations
import json
import math
import sqlite3
import uuid
from collections import deque
from .intent import now,digest


def grams(text, n=2):
    t=' '.join(str(text).casefold().split())
    return {t[i:i+n] for i in range(max(0,len(t)-n+1))} or {t}


class MeaningEngine:
    def __init__(self,ms,audit=None):
        self.ms=ms;self.audit=audit
        with self._db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS edge_events (
             id TEXT PRIMARY KEY, edge_id TEXT NOT NULL, event_type TEXT NOT NULL,
             status TEXT NOT NULL, evidence_refs_json TEXT NOT NULL,
             authority_ref TEXT, reason TEXT NOT NULL, previous_event_id TEXT,
             event_hash TEXT NOT NULL, created_at TEXT NOT NULL,
             FOREIGN KEY(edge_id) REFERENCES semantic_edges(edge_id));
            CREATE TABLE IF NOT EXISTS meaning_proposals (
             proposal_id TEXT PRIMARY KEY, trace_id TEXT NOT NULL,
             candidate_json TEXT NOT NULL, reason TEXT NOT NULL,
             status TEXT NOT NULL DEFAULT 'PENDING', created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS conflict_events (
             conflict_id TEXT PRIMARY KEY, source_cid TEXT NOT NULL, target_cid TEXT NOT NULL,
             edge_ids TEXT NOT NULL, context TEXT, findings TEXT NOT NULL,
             status TEXT NOT NULL DEFAULT 'OPEN', created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS semantic_annotations (
             annotation_id TEXT PRIMARY KEY, cid TEXT NOT NULL,
             axis TEXT NOT NULL, value TEXT NOT NULL, source_ref TEXT NOT NULL,
             created_at TEXT NOT NULL,
             FOREIGN KEY(cid) REFERENCES meaning_cores(cid));
            ''')

    def _db(self):
        db=sqlite3.connect(self.ms.db_path,timeout=15);db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON');return db

    def seed_candidates(self, text, limit=8):
        """Lexical entrypoint, *not* recognition/proof of meaning; graph follows."""
        a=grams(text)
        with self._db() as db:
            rows=db.execute('SELECT cid,surface_form,definition,semantic_coordinates FROM meaning_cores').fetchall()
        matches=[]
        for r in rows:
            b=grams(r['surface_form']+' '+(r['definition'] or ''))
            score=len(a&b)/max(1,len(a|b))
            if r['surface_form'].casefold() in text.casefold():score+=0.6
            if score>0:matches.append({'cid':r['cid'],'seed_score':round(score,5),'method':'lexical_seed_only'})
        return sorted(matches,key=lambda x:(-x['seed_score'],x['cid']))[:limit]

    def resonance(self, seed_cids, depth=2, limit=50, temporal_at=None, context=None):
        """Meaning structure expansion by observed graph edges, not token overlap."""
        depth=min(max(int(depth),0),5);limit=min(max(int(limit),1),500)
        seed_cids=list(dict.fromkeys(cid for cid in seed_cids if self.ms.get_core(cid)))
        queue=deque((cid,0,[cid],[]) for cid in seed_cids)
        visited=set();found=[]
        with self._db() as db:
            edges=[dict(r) for r in db.execute('SELECT * FROM semantic_edges ORDER BY created_at')]
        adjacency={}
        for e in edges:
            if context and e['context'] and e['context']!=context:continue
            if temporal_at and e['temporal_validity']:
                try:
                    tv=json.loads(e['temporal_validity'])
                    if tv.get('from') and temporal_at<tv['from']:continue
                    if tv.get('to') and temporal_at>tv['to']:continue
                except ValueError:continue
            adjacency.setdefault(e['source_cid'],[]).append((e['target_cid'],e))
            if e['direction']=='bidirectional':
                adjacency.setdefault(e['target_cid'],[]).append((e['source_cid'],e))
        while queue and len(found)<limit:
            cid,d,path,edges_path=queue.popleft()
            if cid in visited:continue
            visited.add(cid)
            core=self.ms.get_core(cid)
            found.append({'cid':cid,'core':core,'distance_hops':d,
                          'path_cids':path,'path_edges':edges_path})
            if d>=depth:continue
            for other,e in adjacency.get(cid,[]):
                if other not in visited and other not in path:
                    queue.append((other,d+1,path+[other],edges_path+[e['edge_id']]))
        return {'status':'GRAPH_EXPANDED','candidates':found,'graph_hops':depth,
                'note':'graph adjacency does not prove claim correctness'}

    def candidate_paths(self, start_cid, goal_cid, max_hops=4, limit=12, context=None):
        """Enumerate simple directed typed paths, preserving alternatives and rejections."""
        if not self.ms.get_core(start_cid) or not self.ms.get_core(goal_cid):
            return {'status':'INSUFFICIENT','reason':'unknown_core','candidate_paths':[],'rejected_paths':[]}
        with self._db() as db:
            edges=[dict(r) for r in db.execute('SELECT * FROM semantic_edges ORDER BY edge_id')]
        graph={};reject=[]
        for e in edges:
            if context and e['context'] and e['context']!=context:
                reject.append({'edge_id':e['edge_id'],'reason':'context_mismatch'})
                continue
            graph.setdefault(e['source_cid'],[]).append((e['target_cid'],e))
            if e['direction']=='bidirectional':graph.setdefault(e['target_cid'],[]).append((e['source_cid'],e))
        q=deque([(start_cid,[start_cid],[])]);paths=[]
        while q and len(paths)<limit:
            at,nodes,links=q.popleft()
            if at==goal_cid:
                statuses=[self.edge_status(e['edge_id']) for e in links]
                paths.append({'cids':nodes,'edge_ids':[e['edge_id'] for e in links],
                              'relations':[e['relation_type'] for e in links],
                              'statuses':statuses,
                              'status':'CHECKED_GRAPH_PATH' if statuses and all(s=='VERIFIED' for s in statuses) else 'CANDIDATE_PATH'})
                continue
            if len(links)>=max_hops:continue
            for target,e in graph.get(at,[]):
                if target in nodes:
                    reject.append({'edge_id':e['edge_id'],'reason':'cycle_rejected'})
                    continue
                q.append((target,nodes+[target],links+[e]))
        return {'status':'CANDIDATES' if paths else 'NO_PATH','candidate_paths':paths,
                'rejected_paths':reject[:200],'evaluated_hops':max_hops,
                'independent_real_world_proof':False}

    def edge_status(self, edge_id):
        with self._db() as db:
            row=db.execute('SELECT status FROM edge_events WHERE edge_id=? ORDER BY created_at DESC,id DESC LIMIT 1',(edge_id,)).fetchone()
        return row['status'] if row else 'CANDIDATE'

    def annotate(self,cid,axis,value,source_ref):
        if not self.ms.get_core(cid):raise KeyError(cid)
        if axis not in ('time','place','scale','layer','cluster','context','property'):
            raise ValueError('invalid annotation axis')
        id_=str(uuid.uuid4())
        with self._db() as db:
            db.execute('INSERT INTO semantic_annotations VALUES(?,?,?,?,?,?)',
                       (id_,cid,axis,json.dumps(value,ensure_ascii=False),source_ref,now()))
        return id_

    def propose(self,trace_id,candidate,reason):
        if not isinstance(candidate,dict) or len(candidate.get('meaning_cores',[]))<2 or not candidate.get('relation'):
            raise ValueError('proposal requires two cores and typed relation')
        id_=str(uuid.uuid4())
        with self._db() as db:
            db.execute('INSERT INTO meaning_proposals VALUES(?,?,?,?,?,?)',
                       (id_,trace_id,json.dumps(candidate,ensure_ascii=False,sort_keys=True),reason,'PENDING',now()))
        if self.audit:self.audit.append(trace_id,'MEANING_PROPOSAL',{'proposal_id':id_,'status':'PENDING'})
        return {'status':'PENDING','proposal_id':id_}

    def attest_edge(self,edge_id,evidence_refs,authority_ref,reason,status='VERIFIED'):
        """Manual attestation record; not self-declared independent truth.
        Requires registry evidence, external authority reference. Does not alter original edge.
        """
        if not self.ms.get_edge(edge_id):raise KeyError(edge_id)
        if status not in ('VERIFIED','DISPUTED','REJECTED','RETRACTED'):
            raise ValueError('invalid status')
        if not all([authority_ref,reason]) or not evidence_refs:
            raise ValueError('authority, reason and at least one evidence ref required')
        missing=[ref for ref in evidence_refs if not self.ms.get_evidence(ref)]
        if missing:raise ValueError(f'evidence_not_registered:{missing}')
        with self._db() as db:
            db.execute('BEGIN IMMEDIATE')
            last=db.execute('SELECT id,event_hash FROM edge_events WHERE edge_id=? ORDER BY created_at DESC,id DESC LIMIT 1',(edge_id,)).fetchone()
            id_=str(uuid.uuid4());prev=last['id'] if last else None
            payload={'id':id_,'edge_id':edge_id,'status':status,'evidence_refs':evidence_refs,
                     'authority_ref':authority_ref,'reason':reason,'prev':prev}
            h=digest(payload)
            db.execute('INSERT INTO edge_events VALUES(?,?,?,?,?,?,?,?,?,?)',
                      (id_,edge_id,'ATTEST',status,json.dumps(evidence_refs),authority_ref,reason,prev,h,now()))
        if self.audit:self.audit.append(id_,'EDGE_ATTESTATION',{'edge_id':edge_id,'status':status,'evidence_refs':evidence_refs})
        return {'status':'ATTESTED_RECORDED','edge_id':edge_id,'effective_status':status,'event_id':id_,
                'disclosure':'Recorded authority attestation is not independently verified scientific truth'}

    def detect_conflicts(self):
        """Flag opposing typed edges in same context, conservatively: candidate conflicts."""
        with self._db() as db:
            es=[dict(e) for e in db.execute('SELECT * FROM semantic_edges')]
        positive={'causes':'does_not_cause','is_a':'is_not_a','requires':'does_not_require',
                  'part_of':'not_part_of','affects':'does_not_affect'}
        inverse={v:k for k,v in positive.items()}
        result=[]
        for i,a in enumerate(es):
            for b in es[i+1:]:
                if (a['source_cid'],a['target_cid'],a['context'])!=(b['source_cid'],b['target_cid'],b['context']):continue
                if positive.get(a['relation_type'])==b['relation_type'] or inverse.get(a['relation_type'])==b['relation_type']:
                    result.append({'edge_ids':[a['edge_id'],b['edge_id']],'context':a['context'],
                                   'status':'POTENTIAL_CONFLICT'})
        return result

    def store_conflicts(self):
        findings=self.detect_conflicts()
        for f in findings:
            a=self.ms.get_edge(f['edge_ids'][0]);id_=str(uuid.uuid4())
            with self._db() as db:
                existing=db.execute('SELECT 1 FROM conflict_events WHERE edge_ids=?',(json.dumps(f['edge_ids']),)).fetchone()
                if existing:continue
                db.execute('INSERT INTO conflict_events VALUES(?,?,?,?,?,?,?,?)',
                           (id_,a['source_cid'],a['target_cid'],json.dumps(f['edge_ids']),f['context'],
                            'typed relation opposition','OPEN',now()))
            if self.audit:self.audit.append(id_,'SEMANTIC_CONFLICT',f)
        return findings
