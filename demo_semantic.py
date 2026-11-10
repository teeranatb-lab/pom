"""Reproducible standalone local example. Seed assertions are synthetic test data."""
import json
import tempfile
from pathlib import Path
from olgm.meaning_space import MeaningSpace
from olgm.audit import AuditChain
from olgm.canti import CANTI
from olgm.otfa import OTFA
from olgm.observer import DisabledBackend
from olgm.pipeline import IntegratedRuntime

with tempfile.TemporaryDirectory(prefix='olgm-demo-') as temp:
    db=str(Path(temp)/'demo.db')
    ms=MeaningSpace(db);audit=AuditChain(db);canti=CANTI(db)
    rt=IntegratedRuntime(ms,DisabledBackend(),audit,canti,OTFA(ms),signing_key='test-only-key')
    canti.grant('reason','agent.ask','local_dev',120)
    ms.add_core('water','th','น้ำ','test meaning',origin_ref='example_only')
    ms.add_core('river','th','แม่น้ำ','test meaning',origin_ref='example_only')
    ms.add_edge('flows','water','river','flows_to',origin_ref='example_only')
    response=rt.process('น้ำสัมพันธ์กับแม่น้ำอย่างไร',intent_tag='why',
                        seed_cids=['water'],goal_cid='river')
    print(json.dumps({
        'status':response['status'],
        'answer':response['answer'],
        'proof_type':response['proof_type'],
        'quality':response['quality_proof']['status'],
        'checkpoints':len(response['checkpoints']),
        'audit_verified':audit.verify()[0],
        'not_certified':response['gate_s10']
    },ensure_ascii=False,indent=2))
