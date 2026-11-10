"""S-10: conservative, executable OLGM release-conformance gate.

Two independent ideas are kept separate:
* Mechanism verification: verifiable, reproducible local checks.
* Ultimate release: external Origin authority, trustworthy evidence, live model,
  independent review, security and real-world outcomes must actually exist.

A JSON field such as {"status": "PASS"} is never accepted as proof.
This module does not claim certification or authenticate a real-world identity.
"""
from __future__ import annotations

import hashlib
import sqlite3
import json
import os
import re
import sys
import subprocess
from pathlib import Path
from datetime import datetime,timezone
from .checkpoints import STAGES

RELEASE_GATES = (
    # Stable identifiers: used in machine-readable reports and traceability.
    ('S10-01','Core 0 boundary / Origin declaration', 'F-00 F-01 F-02'),
    ('S10-02','Five Axes independently assessed', 'F-03'),
    ('S10-03','Latest Intent locked, preserved and proven', 'F-04 OP-01 OP-05 OP-10'),
    ('S10-04','Canonical Append+Inherit+Delta and external master verified', 'OP-02'),
    ('S10-05','Meaning Space graph semantics evaluated out-of-sample', 'X-00 OP-04'),
    ('S10-06','T06 live observer independently evaluated', 'OP-04'),
    ('S10-07','T19 V1-V7 / OTFA independently validated', 'OP-03 OP-06'),
    ('S10-08','1+18 method selection / alternatives tested', 'OP-04'),
    ('S10-09','Quality/Logical Gravity/unknown constraints validated', 'OP-06'),
    ('S10-10','CANTI authorization and executed real-world effects', 'OP-07 OP-08'),
    ('S10-11','Audit chain and external immutable anchoring', 'OP-09'),
    ('S10-12','T17 changed weights and blinded heldout improvement', 'OP-04'),
    ('S10-13','Independent provenance and privacy/security assessment', 'OP-09'),
    ('S10-14','Cross-model, adversarial, drift and performance benchmarks', 'OP-04 OP-10'),
    ('S10-15','Origin release authorization and independent reviewer signoff', 'OP-10'),
    ('S10-16','Operational acceptance: security, rollback, monitors', 'OP-07 OP-08 OP-09'),
    ('S10-17','G06 self-modification: sandbox, signed approval, rollback, and blind generalization', 'OP-04 OP-06 OP-07 OP-09 OP-10'),
    ('S10-18','Thai understanding/retrieval learning: blind linguistic and safety evaluation','X-00 OP-03 OP-04 OP-09'),
    ('S10-19','Thai code generation: functionality, security and provenance conformance','OP-04 OP-06 OP-07 OP-09'),
    ('S10-20','Intellectual sovereignty: Origin authorization, no exfiltration, lineage and independent review','F-00 F-01 F-02 OP-02 OP-09 OP-10'),
    ('S10-21','High-value valueguard: measured forecast, origin-first delivery, family attestation, privacy & lawful notice','F-01 OP-03 OP-06 OP-09 OP-10'),
)


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def source_manifest(root):
    """Hash only project-owned runtime sources; no secrets, DBs or personal files."""
    root=Path(root).resolve()
    names=[root/'runtime.py']+sorted((root/'olgm').rglob('*.py'))+sorted((root/'tests').rglob('test_*.py'))
    return {str(p.relative_to(root)):sha256(p) for p in names if p.is_file()}


def check_evidence_manifest(manifest_path, evidence_root, trusted_public_keys=None):
    """Verify artifact bytes + Ed25519 signatures; local key enrollment is not identity proof.

    Manifest schema:
      {"items":[{"gate_id":"S10-06", "artifact":"t06/independent.json",
        "sha256":"...", "signer":"reviewer-a", "signature_hex":"..."}]}
    Sign bytes UTF-8 of: "OLGM-S10|<gate_id>|<artifact>|<sha256>".
    `artifact` must be a regular file located strictly under `evidence_root`.
    Signer keys must be supplied independently by the operator. This is a
    cryptographic integrity check, NOT proof of independence, correctness or
    accreditation of the signed assertion.
    """
    root=Path(evidence_root).resolve()
    keys=trusted_public_keys or {}
    result={}
    try:
        document=json.loads(Path(manifest_path).read_text(encoding='utf-8'))
        if not isinstance(document,dict) or not isinstance(document.get('items'),list):
            raise ValueError('manifest_missing_items')
    except (OSError,ValueError) as exc:
        return {'status':'FAIL','reason':'invalid_manifest','detail':str(exc),'items':[]}
    for n,item in enumerate(document['items']):
        try:
            gate=item['gate_id'];relative=item['artifact'];expected=item['sha256']
            signer=item['signer'];signature=item['signature_hex']
            if gate not in {g[0] for g in RELEASE_GATES}:raise ValueError('unknown_gate')
            if not isinstance(relative,str) or not relative or Path(relative).is_absolute() or '..' in Path(relative).parts:
                raise ValueError('bad_relative_path')
            path=(root/relative).resolve(strict=True)
            if not path.is_relative_to(root) or not path.is_file():
                raise ValueError('path_escape_or_not_file')
            if not re.fullmatch(r'[0-9a-f]{64}',expected):raise ValueError('bad_sha256')
            actual=sha256(path)
            if actual!=expected:raise ValueError('artifact_hash_mismatch')
            if signer not in keys:raise ValueError('signer_not_in_trusted_keyring')
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            pub=Ed25519PublicKey.from_public_bytes(bytes.fromhex(keys[signer]))
            signed=f'OLGM-S10|{gate}|{relative}|{expected}'.encode('utf-8')
            pub.verify(bytes.fromhex(signature),signed)
            status={'index':n,'gate_id':gate,'artifact':relative,'signer':signer,
                    'status':'CRYPTOGRAPHIC_INTEGRITY_VALID',
                    'limitation':'Signature attests to bytes and enrolled key, not factual truth or independent signer identity'}
        except Exception as exc:
            # Fail closed on absent keys, malformed signatures, path traversal,
            # hash mismatch. Never silently accept unverifiable evidence.
            status={'index':n,'gate_id':item.get('gate_id') if isinstance(item,dict) else None,
                    'status':'REJECTED','reason':type(exc).__name__+':'+str(exc)[:180]}
        result[n]=status
    values=list(result.values())
    return {'status':'INTEGRITY_VERIFIED' if values and all(
                    v['status']=='CRYPTOGRAPHIC_INTEGRITY_VALID' for v in values) else 'FAIL',
            'items':values,'independent_review':'NOT_ESTABLISHED_BY_CRYPTOGRAPHY'}


def evaluate(rt, trace_id=None, test_capture=None, evidence_manifest=None,
             evidence_root=None, trusted_keys=None):
    """Read-only S10 evaluation: missing information is blocking, never inferred PASS.

    Reports are evidence inventories, not certificates. At the code level an
    observed PASS proves only its narrowly named mechanism. No single trace or
    test suite is a valid final S-10 acceptance proof.
    """
    try:
        chain_ok,chain_message=rt.audit.verify()
        with rt.audit._conn() as db:
            audit_count=db.execute('SELECT COUNT(*) FROM audit_chain').fetchone()[0]
        checkpoints=rt.checkpoints.verify(trace_id)
        canonical=rt.canonical.verify()
        trace=[]
        if trace_id:
            trace=rt.checkpoints.for_trace(trace_id)
    except (sqlite3.Error,OSError,ValueError) as exc:
        return {'gate':'S-10','overall':'FAIL','release_authorized':False,
                'assurance_level':'UNTRUSTED_LOCAL_STATE',
                'trace_id':trace_id,
                'reason':'audit_checkpoint_or_database_unreadable',
                'error_type':type(exc).__name__,
                'gates':[{'gate_id':g[0],'status':'FAIL','reason':'cannot_verify_integrity'}
                         for g in RELEASE_GATES],
                'counts':{'required':len(RELEASE_GATES),'passed':0,'blocked':0,
                          'failed':len(RELEASE_GATES)},
                'disclosure':'No damaged database or unreadable chain may yield a release PASS'}
    stage_list=[x['stage'] for x in trace]
    complete_trace=bool(trace_id and stage_list==list(STAGES))
    if trace_id and (not complete_trace):
        trace_status='FAIL' if trace else 'NOT_TESTED'
    else:trace_status='PASS' if complete_trace and checkpoints.get('status')=='PASS' else 'NOT_TESTED'
    status_by_stage={r['stage']:r['status'] for r in trace}
    trace_findings={
        'status':trace_status,
        'expected_stages':list(STAGES),
        'observed_stages':stage_list,
        'all_stages_in_exact_order':complete_trace,
        'stage_statuses':status_by_stage,
        'all_stages_pass':complete_trace and all(r['status']=='PASS' for r in trace),
        'disclosure':'Presence of a stage is not proof it passed',
    }
    capture=None
    if test_capture:
        try:
            capture=json.loads(Path(test_capture).read_text(encoding='utf-8'))
            if not isinstance(capture,dict):raise ValueError('not_object')
            # Only locally generated capture with the exact source hash is evidence
            # for tested mechanics; arbitrary PASS labels are not accepted.
            expected=capture.get('source_sha256')
            current=source_manifest(Path(__file__).resolve().parent.parent)
            stdout=capture.get('stdout','')
            counts_from_log={}
            if isinstance(stdout,str):
                for n,k in re.findall(r'(\d+)\s+(passed|failed|skipped|error|errors)',stdout):
                    key='errors' if k in ('error','errors') else k
                    counts_from_log[key]=int(n)
            plausible=bool(counts_from_log.get('passed',0)>0 and
                all(capture.get(k,0)==counts_from_log.get(k,0) for k in
                    ('passed','failed','skipped','errors')) and
                capture.get('command')==['python','-m','pytest','-q','-ra'])
            capture={'status':'LOCAL_TEST_LOG_AND_SOURCE_MATCH' if capture.get('returncode')==0 and
                     capture.get('failed',0)==0 and expected==current and plausible else 'REJECTED',
                     'passed':capture.get('passed',0),'skipped':capture.get('skipped',0),
                     'failed':capture.get('failed',0),'returncode':capture.get('returncode'),
                     'hash_matches_current_sources':expected==current,'log_summary_matches_counts':plausible,
                     'disclosure':'pytest log is local verification, not independent attestation'}
        except (OSError,ValueError) as exc:
            capture={'status':'REJECTED','reason':str(exc)}
    attestation=None
    if evidence_manifest:
        attestation=check_evidence_manifest(evidence_manifest,evidence_root or '.',trusted_keys)

    mechanical={
        'audit_chain':{'status':'PASS' if chain_ok and audit_count else
                  'NOT_TESTED' if chain_ok else 'FAIL', 'count':audit_count,'detail':chain_message},
        'checkpoint_integrity':dict(checkpoints,status='NOT_TESTED') if checkpoints.get('status')=='PASS' and checkpoints.get('count')==0 else checkpoints,
        'canonical_ledger':canonical,
        'full_trace_recorded':trace_findings,
        'local_test_capture':capture or {'status':'NOT_TESTED'},
    }
    # These gates cannot be satisfied merely by an LLM assertion, local test,
    # signer's self-attestation, or a document existing on disk.
    gates=[]
    external_proofs={'S10-01':'Origin declaration/identity independently authenticated',
         'S10-02':'Independent five-axis ethical audit',
         'S10-03':'Authenticated identity and replay/delta cross-session evaluation',
         'S10-04':'Original Canonical PDF independently hash-verified and authorized',
         'S10-05':'Blind semantic benchmark with disclosed corpus and labels',
         'S10-06':'Live model observations and blind evaluation on heldout paraphrases',
         'S10-07':'Independent verifier/source credibility/entailment and temporal validation',
         'S10-08':'Documented independent cognitive-method effectiveness evaluation',
         'S10-09':'Independent measured gate calibration and policy decisions',
         'S10-10':'Authorized real-world action and externally observed effects',
         'S10-11':'Independent immutable timestamp/anchor and tamper recovery exercise',
         'S10-12':'Actual training checkpoint + hashes + blind before/after benchmark',
         'S10-13':'Independent threat model, PDPA/privacy review and security penetration tests',
         'S10-14':'Cross-provider adversarial, regression and latency/cost measurements',
         'S10-15':'Explicit Origin signature plus independent reviewer acceptance',
         'S10-16':'Production-specific identity/TLS/monitoring/backup/restore/rollback tests',
         'S10-17':'Independent G06 novel capability test, source mutation authorization, adversarial benchmark and rollback evidence',
         'S10-18':'Independent heldout Thai corpus including ambiguity, OOV, paraphrases, spelling and factuality',
         'S10-19':'Independent novel-code benchmark, property tests, code scan, security sandbox and Origin source-use permission',
         'S10-20':'Out-of-band Origin identity proof, consent/licensing audit, no-leak review and independent reviewer approval',
         'S10-21':'Independent value-model validation, SMTP owner-first delivery proof, real Origin/family identity checks, privacy law and user-notice review'}
    for gate_id,title,stages in RELEASE_GATES:
        missing=[s for s in stages.split() if status_by_stage.get(s)!='PASS']
        gate_status='FAIL' if not chain_ok or checkpoints.get('status')=='FAIL' or \
            (trace_id and trace_status=='FAIL') else 'BLOCKED'
        gates.append({'gate_id':gate_id,'name':title,'status':gate_status,
             'checkpoint_refs':stages.split(), 'nonpass_checkpoints':missing,
             'independent_proof_required':external_proofs[gate_id],
             'artifact_signature_is_not_claim_validation':True})
    overall='FAIL' if any(g['status']=='FAIL' for g in gates) else 'NOT_PASSED'
    return {'gate':'S-10','overall':overall,'release_authorized':False,
        'assurance_level':'LOCAL_MECHANISM_ONLY',
        'evaluated_at':datetime.now(timezone.utc).isoformat(),
        'trace_id':trace_id,'mechanical_checks':mechanical,
        'evidence_attestations':attestation or {'status':'NOT_SUBMITTED'},
        'gates':gates,'counts':{
            'required':len(gates),'passed':0,
            'blocked':sum(g['status']=='BLOCKED' for g in gates),
            'failed':sum(g['status']=='FAIL' for g in gates)},
        'next_action':'Collect independent, source-bound proof for every gate; do not self-declare PASS.',
        'limitations':['T06_LIVE_NOT_AUTOMATICALLY_PROVEN','T17_WEIGHT_LEARNING_NOT_AUTOMATICALLY_PROVEN',
                       'INDEPENDENT_SOURCE_TRUTH_NOT_AUTOMATICALLY_PROVEN',
                       'ORIGIN_IDENTITY_NOT_AUTOMATICALLY_AUTHENTICATED',
                       'EXTERNAL_ACTION_EFFECT_NOT_AUTOMATICALLY_VERIFIED']}


def capture_pytest(project_root, target_path, timeout=180):
    """Run actual local tests and bind output to source snapshot. No synthetic PASS."""
    root=Path(project_root).resolve(); output=Path(target_path)
    if not (root/'pytest.ini').is_file():raise ValueError('not_project_root')
    env=os.environ.copy()
    env['OLGM_ENV']='development'  # independent local code test; never production attestation
    # Avoid accidentally triggering external model endpoints during local capture.
    for key in ('OLGM_BASE','OLGM_MODEL','OLGM_CKPT_BEFORE','OLGM_CKPT_AFTER',
                'OLGM_BENCH_BEFORE','OLGM_BENCH_AFTER'):
        env.pop(key,None)
    try:
        p=subprocess.run([sys.executable,'-m','pytest','-q','-ra'],cwd=root,
                         capture_output=True,text=True,timeout=timeout,env=env)
        textout=p.stdout+'\n'+p.stderr
        rc=p.returncode
    except subprocess.TimeoutExpired as exc:
        textout='TEST RUN TIMED OUT: '+str(exc);rc=124
    counts={v:0 for v in ('passed','failed','skipped','errors')}
    for name,num in re.findall(r'(\d+)\s+(passed|failed|skipped|error|errors)',textout):
        key='errors' if num in ('error','errors') else num
        counts[key]=int(name)
    artifact={'status':'COMPLETED' if rc==0 else 'FAILED','returncode':rc,**counts,
            'source_sha256':source_manifest(root),
            'python':sys.version,'command':['python','-m','pytest','-q','-ra'],
            'recorded_at':datetime.now(timezone.utc).isoformat(),
            'stdout':textout[-50000:],
            'external_model_invoked':False,
            'live_test_status':'NOT_TESTED_BY_THIS_COMMAND',
            'independent_reviewer':'NONE'}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(artifact,ensure_ascii=False,indent=2),encoding='utf-8')
    return {k:v for k,v in artifact.items() if k not in ('stdout','source_sha256','python')}
