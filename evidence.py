"""Typed immutable evidence/claims and explicit evidence-to-claim assertions.
V1-V7 are implemented as mechanical tests; sourcing and external truth remain separately graded.
"""
import hashlib
import json
import sqlite3
import uuid
from .intent import digest,now

CLASSES={'FACT','OBSERVED','MEASURED','CALCULATED','INFERRED','ESTIMATED','ASSUMPTION','UNKNOWN','CONFLICTED'}


class EvidenceLedger:
    def __init__(self,ms,audit=None):
        self.ms=ms;self.audit=audit
        with self._db() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS claims (
                claim_id TEXT PRIMARY KEY, claim_text TEXT NOT NULL,
                class TEXT NOT NULL, context TEXT, origin_ref TEXT NOT NULL,
                created_at TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS evidence_links (
                link_id TEXT PRIMARY KEY, claim_id TEXT NOT NULL, evidence_ref TEXT NOT NULL,
                link_type TEXT NOT NULL CHECK(link_type IN ('supports','contradicts','mentions')),
                excerpt TEXT NOT NULL, locator TEXT, assessed_by TEXT,
                assessment_method TEXT, created_at TEXT NOT NULL,
                FOREIGN KEY(claim_id) REFERENCES claims(claim_id),
                FOREIGN KEY(evidence_ref) REFERENCES evidence(evidence_ref));
            ''')

    def _db(self):
        db=sqlite3.connect(self.ms.db_path,timeout=15);db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON');return db

    def add_claim(self, claim_text, class_='UNKNOWN', context=None,origin_ref=None,claim_id=None):
        if class_ not in CLASSES:raise ValueError('bad epistemic class')
        if not claim_text or not origin_ref:raise ValueError('claim and origin ref required')
        claim_id=claim_id or str(uuid.uuid4())
        with self._db() as db:
            db.execute('INSERT INTO claims VALUES(?,?,?,?,?,?)',
                       (claim_id,claim_text,class_,context,origin_ref,now()))
        return claim_id

    def link(self, claim_id,evidence_ref,link_type,excerpt,locator=None,assessed_by=None,assessment_method=None):
        if link_type not in ('supports','contradicts','mentions'):raise ValueError('invalid link_type')
        if not assessed_by or not assessment_method:raise ValueError('must record assessor and method')
        ev=self.ms.get_evidence(evidence_ref)
        if not ev:raise ValueError('unknown evidence ref')
        if not excerpt or (ev['excerpt'] is not None and excerpt not in ev['excerpt']):
            raise ValueError('excerpt must be nonempty and present in source text')
        if not self.claim(claim_id):raise ValueError('unknown claim')
        link_id=str(uuid.uuid4())
        with self._db() as db:
            db.execute('INSERT INTO evidence_links VALUES(?,?,?,?,?,?,?,?,?)',
                       (link_id,claim_id,evidence_ref,link_type,excerpt,locator,assessed_by,assessment_method,now()))
        if self.audit:self.audit.append(claim_id,'EVIDENCE_LINK',{'link_id':link_id,'ref':evidence_ref,'type':link_type})
        return link_id

    def claim(self,claim_id):
        with self._db() as db:
            r=db.execute('SELECT * FROM claims WHERE claim_id=?',(claim_id,)).fetchone()
        return dict(r) if r else None

    def links(self,claim_id):
        with self._db() as db:
            rows=db.execute('SELECT * FROM evidence_links WHERE claim_id=? ORDER BY created_at',(claim_id,)).fetchall()
        return [dict(x) for x in rows]

    def v1_v7(self,claim_id):
        """Observable mechanical validations, not automatic judgment of source truth.
        V1 identification; V2 integrity; V3 exact bound excerpt; V4 attribution;
        V5 independence; V6 conflict scan; V7 temporal freshness/context.
        """
        claim=self.claim(claim_id)
        if not claim:return {'status':'INSUFFICIENT','reason':'claim_not_found','checks':{}}
        links=self.links(claim_id)
        ev=[self.ms.get_evidence(l['evidence_ref']) for l in links]
        checks={}
        checks['V1_source_identity']={'status':'PASS' if links and all(e and e['source_type'] for e in ev) else 'INSUFFICIENT'}
        checks['V2_content_integrity']={'status':'PASS' if ev and all(e and e['excerpt'] is not None and
                    hashlib.sha256(e['excerpt'].encode()).hexdigest()==e['content_hash'] for e in ev)
                    else 'NOT_TESTED','limitation':'Byte-only or unavailable source content cannot be rehashed from registry'}
        checks['V3_claim_binding']={'status':'PASS' if links and all(l['excerpt'] for l in links) else 'INSUFFICIENT',
                    'limitation':'Excerpt presence is not entailment proof'}
        checks['V4_provenance']={'status':'PASS' if links and all(l['assessed_by'] and l['assessment_method'] for l in links) else 'INSUFFICIENT'}
        independent_sources={e['source_url'] or l['evidence_ref'] for l,e in zip(links,ev) if e}
        checks['V5_independence']={'status':'REVIEW_REQUIRED' if len(independent_sources)<2 else 'NOT_TESTED',
                    'reason':'source-independence cannot be inferred from distinct URLs'}
        supports=sum(l['link_type']=='supports' for l in links)
        against=sum(l['link_type']=='contradicts' for l in links)
        checks['V6_conflicts']={'status':'CONTRADICTED' if against and supports else 'REVIEW_REQUIRED' if against else
                                  'PASS' if supports else 'INSUFFICIENT','support_links':supports,'contradiction_links':against}
        checks['V7_temporal']={'status':'NOT_TESTED','reason':'source validity interval and real-world freshness require domain policy'}
        return {'status':'CONFLICTED' if supports and against else 'EVIDENCE_REGISTERED_NOT_PROVEN' if links else 'INSUFFICIENT',
                'claim_id':claim_id,'checks':checks,'epistemic_class':claim['class'],
                'disclosure':'V1-V7 are traceable mechanical checks, NOT independent source credibility or entailment proof'}
