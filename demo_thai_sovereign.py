"""Purely local demonstration using an EPHEMERAL test identity.

The private key generated here belongs to an artificial TEST Origin, not the
real OLGM Origin. Never use a demo key or test approval for production.
Run: python examples/demo_thai_sovereign.py --output docs/THAI_DEMO_REPORT.json
"""
from pathlib import Path
import argparse
import json
import os
import tempfile
from datetime import datetime,timedelta,timezone
from olgm.audit import AuditChain
from olgm.meaning_space import MeaningSpace
from olgm.canti import CANTI
from olgm.intent import digest
from olgm.identity import SignedAuthorizations
from olgm.thai.learning import ThaiExampleMemory
from olgm.thai.lexicon import ThaiLexicon
from olgm.thai.responder import ThaiResponder
from olgm.thai.codegen import SafeCodeGenerator
from olgm.thai.patterns import stats


def main():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    parser=argparse.ArgumentParser()
    parser.add_argument('--output')
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='olgm_thai_demo_') as temp:
        db=str(Path(temp)/'demo.db')
        ms=MeaningSpace(db);audit=AuditChain(db);canti=CANTI(db)
        examples=ThaiExampleMemory(db,audit,canti)
        lex=ThaiLexicon(ms,canti,audit)
        responder=ThaiResponder(examples,lexicon=lex)
        before=responder.answer('คุณลักษณะการเรียนรู้ทดสอบจำกัด')['status']
        key=Ed25519PrivateKey.generate()
        public=key.public_key().public_bytes(encoding=serialization.Encoding.Raw,
                                             format=serialization.PublicFormat.Raw).hex()
        SignedAuthorizations(db).enroll_public_key('TEST_ORIGIN_NOT_REAL',public,'Origin','EPHEMERAL_TEST_FIXTURE')
        canti.grant('sandbox_train','thai.examples','test_only',180)
        canti.grant('sandbox_write','thai.lexicon','test_only',180)
        canti.grant('sandbox_train','thai.lexicon','test_only',180)
        canti.grant('sandbox_write','thai.generated','test_only',180)
        example=examples.propose('คุณลักษณะการเรียนรู้ทดสอบจำกัด',
             'ระบบทดสอบนี้เก็บตัวอย่างพร้อมที่มาและการอนุมัติเฉพาะที่',
             'synthetic-origin-ref','synthetic-source-ref','synthetic-test-license','demo')
        before_approval=examples.approved_match('คุณลักษณะการเรียนรู้ทดสอบจำกัด')
        expiry=(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()
        receipt=examples.approval_receipt(example['example_id'],'TEST_ORIGIN_NOT_REAL',expiry)
        approved=examples.approve(example['example_id'],receipt,key.sign(digest(receipt).encode()).hex())
        after=responder.answer('คุณลักษณะการเรียนรู้ทดสอบจำกัด')
        ms.add_core('WATER-DEMO','th','น้ำ',definition='ของเหลว',origin_ref='synthetic-origin-ref')
        before_core=ms.get_core('WATER-DEMO')
        candidate=lex.propose('ธาราทดสอบ','WATER-DEMO','synthetic-origin-ref','synthetic-source-ref','test-license')
        alias_receipt=lex.approval_receipt(candidate['alias_id'],'TEST_ORIGIN_NOT_REAL',expiry)
        alias_status=lex.approve(candidate['alias_id'],alias_receipt,
                                    key.sign(digest(alias_receipt).encode()).hex())
        lexical_response=responder.answer('ธาราทดสอบแปลว่าอะไร')
        core_unchanged=ms.get_core('WATER-DEMO')==before_core
        codegen=SafeCodeGenerator(output_root=Path(temp)/'generated',canti=canti)
        code=codegen.render_pipeline(['unique','sort'],origin_ref='synthetic-origin-ref')
        saved=codegen.save(code,'thai_demo_unique_sort.py')
        code_artifact_sha256=saved['source_sha256']
        ok,detail=audit.verify()
        report={
            'scope':'LOCAL_DEMONSTRATION_WITH_SYNTHETIC_TEST_ORIGIN',
            'real_origin_identity_proved':False,'canonical_modified':False,
            'live_model_used':False,'network_used':False,
            'source_license':'synthetic-test-license',
            'pattern_catalog':stats(),
            'learning_before':before,
            'candidate_not_served_before_approval':before_approval is None,
            'example_approval':approved['status'],
            'learning_after':after['status'],
            'learned_answer_th':after['answer_th'],
            'lexicon_approval':alias_status['status'],
            'lexicon_response':lexical_response['answer_th'],
            'lexicon_original_cid_unchanged':core_unchanged,
            'generated_code_pattern':code['pattern'],
            'generated_code_sha256':code_artifact_sha256,
            'generated_output_class':'CANDIDATE_NOT_PRODUCTION',
            'audit_verified':ok,'audit_detail':detail,
            'release':'NOT_S10_PASSED',
        }
    if args.output:
        out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
