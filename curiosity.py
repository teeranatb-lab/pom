"""Bounded, non-executing curiosity generates follow-up hypotheses within Meaning Space."""
import uuid
from .intent import now


class BoundedCuriosity:
    def __init__(self,semantic,audit=None,max_items=3):
        self.sem=semantic;self.audit=audit
        self.max_items=max(0,min(int(max_items),10))

    def suggest(self,trace_id,seed_cids):
        if not self.max_items:return {'status':'DISABLED','recommendations':[]}
        graph=self.sem.resonance(seed_cids,depth=2,limit=100)
        suggestions=[]
        conflicts=self.sem.detect_conflicts()
        for c in conflicts:
            suggestions.append({'kind':'CONFLICT','question':'ตรวจสอบความขัดแย้งของเส้นความสัมพันธ์',
                                'edge_ids':c['edge_ids'],'priority':'review_first',
                                'state':'CANDIDATE_NOT_FACT'})
        for x in graph['candidates']:
            if len(suggestions)>=self.max_items:break
            cid=x['cid']
            with self.sem._db() as db:
                rows=db.execute('''SELECT edge_id FROM semantic_edges WHERE source_cid=? OR target_cid=?''',
                                (cid,cid)).fetchall()
            if not rows:
                suggestions.append({'kind':'GAP','question':'ความหมายนี้สัมพันธ์กับแก่นใดบ้าง?',
                                    'cid':cid,'state':'CANDIDATE_NOT_FACT'})
                continue
            for r in rows:
                if len(suggestions)>=self.max_items:break
                eid=r['edge_id']
                if self.sem.edge_status(eid)!='VERIFIED':
                    suggestions.append({'kind':'EVIDENCE_GAP','question':'มีหลักฐานอิสระรองรับเส้นนี้หรือไม่?',
                                        'edge_id':eid,'state':'CANDIDATE_NOT_FACT'})
        suggestions=suggestions[:self.max_items]
        if self.audit:self.audit.append(trace_id,'BOUNDED_CURIOSITY',
                                        {'count':len(suggestions),'items':suggestions})
        return {'status':'SUGGESTIONS_ONLY','budget':self.max_items,
                'recommendations':suggestions,'tool_executions':0}
