"""Run from project root: python examples/demo_control_access.py.

Uses a temporary database and ephemeral TEST key. No real computer action,
ChatGPT plugin invocation, Space access, or persistent credentials.
"""
from __future__ import annotations
import json,sys,tempfile
from datetime import datetime,timezone,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from olgm.audit import AuditChain
from olgm.canti import CANTI
from olgm.identity import SignedAuthorizations
from olgm.intent import IntentLedger
from olgm.meaning_space import MeaningSpace
from olgm.control import ResourceRegistry,ControlPlane,ConnectorDispatcher
from olgm.control.registry import digest
from olgm.control.skills import BuiltinSkillExecutor,installed_skill_id

with tempfile.TemporaryDirectory(prefix='olgm_control_demo_') as tmp:
    db=str(Path(tmp)/'olgm.sqlite3')
    MeaningSpace(db)
    audit=AuditChain(db);canti=CANTI(db);intents=IntentLedger(db,audit)
    auth=SignedAuthorizations(db);registry=ResourceRegistry(db)
    control=ControlPlane(db,registry,intents,canti,auth,audit)
    # No device or ChatGPT connector is contacted by these declarations.
    registry.register('computer.xadmin-v1','computer','X-admin','local-desktop',
          ['computer.status','computer.screenshot'],'RESTRICTED','origin-ref','user-declared','OFFLINE')
    registry.register('plugin.demo-v1','plugin','Demo plugin','connector-adapter',
          ['plugin.describe','plugin.invoke'],'INTERNAL','origin-ref','example',
          'NOT_CONNECTED',targets=['documents.search'])
    registry.register('space.demo-v1','space','Demo Space','connector-adapter',
          ['space.list','space.read'],'PRIVATE','origin-ref','example',
          'NOT_CONNECTED',targets=['page.demo'])
    sk=BuiltinSkillExecutor(registry,control,audit,intents,canti)
    sk.install('connection_gaps','origin-ref')
    key=Ed25519PrivateKey.generate()
    pub=key.public_key().public_bytes(encoding=serialization.Encoding.Raw,
                 format=serialization.PublicFormat.Raw).hex()
    auth.enroll_public_key('demo-test-origin',pub,'Origin','test-key-only')
    locked=intents.create('demo-user','origin-ref','ตรวจสอบรายการเครื่องและช่องว่างการเชื่อมต่อ',task_type='WORK')
    rid=installed_skill_id('connection_gaps')
    proposal=control.propose(locked['intent_id'],locked['intent_hash'],rid,'skill.run',{},
                             'demo-user','demo-unique-001')
    canti.grant('skill_run',rid,'development_fixture',ttl=180)
    receipt=control.receipt(proposal['plan_id'],'demo-test-origin',
             (datetime.now(timezone.utc)+timedelta(minutes=3)).isoformat(),'demo-approval')['receipt']
    signature=key.sign(digest(receipt).encode()).hex()
    approval=control.approve(proposal['plan_id'],receipt,signature)
    queued=control.enqueue(proposal['plan_id'])
    connector=ConnectorDispatcher(handlers={rid:
        (lambda action,args,idempotency_key:sk.handler('connection_gaps',action,args,idempotency_key))})
    result=control.work_once(connector)
    chain_ok,detail=audit.verify()
    report={'scenario':'LOCAL_SIMULATED_CONNECTORS_NO_REAL_CONTROL',
            'declared_resources':len(registry.list()['resources']),
            'proposal':proposal['status'], 'approval':approval['status'],
            'queue':queued['status'],'execution':result,'audit_verified':chain_ok,
            'audit_detail':detail,'s10':'NOT_PASSED'}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if (proposal['status']!='PENDING_APPROVAL' or approval['status']!='APPROVED'
            or result['status']!='COMPLETED' or not chain_ok):
        sys.exit(1)
