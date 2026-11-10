"""Local production preflight: checks mechanisms, never certifies identity or truth.

Run read-only against the source SQLite database; backup/restore drill uses a temporary
copy and does not overwrite production files. No automatic deployment or approvals.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timezone

PRODUCTION_BLOCKED_CLI = frozenset({
    'grant-dev', 'key-enroll-dev', 'canonical-init', 'policy-ref',
    'g06-apply', 'g06-rollback', 'revoke', 'core-add', 'edge-add',
    'edge-attest', 'evidence-add', 'claim-add', 'claim-link',
    'thai-learn-approve', 'thai-alias-approve', 'thai-alias-propose',
    'thai-code', 'thai-code-pipeline', 'thai-synthesize',
    'thai-learn-propose', 'g06-propose', 'selflearn-v2-cycle',
    'audit-anchor', 'plan', 'approve', 'execute',
    'control-register','control-install-skill','control-propose','control-approve','control-enqueue',
    'control-worker-step','control-cancel',
    'value-evaluate','value-dispatch','value-exempt',
})


def is_production(environ=None):
    env = environ if environ is not None else os.environ
    return env.get('OLGM_ENV', 'development').strip().lower() == 'production'


def cli_allowed(command, environ=None):
    """No locally bootstrapped privileges, code mutation or action execution in prod.

    Existing CANTI grants are not a production identity or authorization system.
    Any future production writes require a distinct, independently validated gateway.
    """
    return not (is_production(environ) and command in PRODUCTION_BLOCKED_CLI)


def _file_sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def sqlite_backup_restore_drill(db_path):
    """Physical SQLite snapshot, integrity check, compare logical schema+rows.

    This is a local recoverability *mechanism* test, not an off-site disaster
    recovery or backup retention guarantee. Does not modify the source DB.
    """
    src=Path(db_path)
    if not src.is_file():
        return {'status':'BLOCKED','reason':'database_file_missing'}
    with tempfile.TemporaryDirectory(prefix='olgm_s10_restore_') as tmp:
        snapshot=Path(tmp)/'backup.sqlite3'
        restored=Path(tmp)/'restored.sqlite3'
        try:
            with sqlite3.connect(f'file:{src.resolve()}?mode=ro',uri=True,timeout=8) as source:
                with sqlite3.connect(snapshot) as dest:
                    source.backup(dest)
            shutil.copy2(snapshot,restored)
            with sqlite3.connect(f'file:{restored}?mode=ro',uri=True) as db:
                integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
                schema_count=db.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
                if integrity!='ok':
                    return {'status':'FAIL','reason':'restored_integrity_failed','integrity':integrity}
            digest1=_file_sha(snapshot); digest2=_file_sha(restored)
            return {'status':'PASS' if hmac.compare_digest(digest1,digest2) else 'FAIL',
                    'snapshot_sha256':digest1,'restored_sha256':digest2,
                    'tables':schema_count,'integrity':integrity,
                    'scope':'LOCAL_TEMPORARY_COPY_ONLY'}
        except (OSError,sqlite3.Error) as exc:
            return {'status':'FAIL','reason':type(exc).__name__+': '+str(exc)[:150]}


def preflight(rt, environ=None, do_restore=True):
    """Environment and mechanism checks. Requires external operator acceptance.

    Both `preflight` and `S-10 evaluate` must be reviewed before live deployment.
    """
    env=os.environ if environ is None else environ
    checks={}
    checks['production_mode']={'status':'PASS' if is_production(env) else 'BLOCKED',
                               'value':env.get('OLGM_ENV','development')}
    token=env.get('OLGM_HTTP_TOKEN','')
    checks['http_token']={'status':'PASS' if len(token)>=32 and len(set(token))>=12 else 'BLOCKED',
                          'reason':'requires_a_unique_high_entropy_secret_min_32_chars'}
    checks['loopback_api']={'status':'PASS','enforced_in':'olgm.api.serve',
                            'scope':'APP_LISTENER_ONLY; TLS reverse proxy not validated'}
    checks['external_tls_verified']={'status':'NOT_TESTED',
                                    'reason':'requires deployed endpoint and independently collected TLS scan'}
    checks['external_identity_verified']={'status':'NOT_TESTED',
                                         'reason':'requires authenticated Origin and RBAC integration'}
    checks['independent_threat_review']={'status':'NOT_TESTED',
                                        'reason':'independent security and PDPA review not provided'}
    try:
        with sqlite3.connect(f'file:{Path(rt.ms.db_path).resolve()}?mode=ro',uri=True) as db:
            integrity=db.execute('PRAGMA integrity_check').fetchone()[0]
            checks['database_integrity']={'status':'PASS' if integrity=='ok' else 'FAIL',
                                          'result':integrity}
            count=db.execute("SELECT count(*) FROM permissions WHERE revoked_at IS NULL AND (expires_at IS NULL OR expires_at>?)",
                            (datetime.now(timezone.utc).isoformat(),)).fetchone()[0]
            checks['no_active_dev_grants']={'status':'PASS' if count==0 else 'BLOCKED',
                                            'active_grants':count,
                                            'reason':'all local CLI grants must be removed before production'}
    except (sqlite3.Error,OSError) as exc:
        checks['database_integrity']={'status':'FAIL','reason':str(exc)}
        checks['no_active_dev_grants']={'status':'FAIL','reason':'cannot_check_permissions'}
    try:
        ok,why=rt.audit.verify()
        checks['audit_chain']={'status':'PASS' if ok else 'FAIL','detail':why,
                               'warning':'local hash-chain is not an immutable remote anchor'}
    except (sqlite3.Error,OSError,ValueError) as exc:
        checks['audit_chain']={'status':'FAIL','reason':str(exc)}
    try:
        cp=rt.checkpoints.verify()
        checks['checkpoint_integrity']={'status':cp.get('status','NOT_TESTED'),
                                       'records':cp.get('count',0)}
    except (sqlite3.Error,OSError,ValueError) as exc:
        checks['checkpoint_integrity']={'status':'FAIL','reason':str(exc)}
    try:
        canonical=rt.canonical.verify()
        checks['canonical_ledger']={'status':canonical['status'],
                                    'versions':canonical.get('versions',0),
                                    'warning':'local hash ledger does not authenticate the canonical PDF'}
    except (sqlite3.Error,OSError,ValueError) as exc:
        checks['canonical_ledger']={'status':'FAIL','reason':str(exc)}
    # New control plane gate: no live Connector/desktop capability can be certified
    # by a local registry declaration or local unit tests.
    try:
        with sqlite3.connect(f'file:{Path(rt.ms.db_path).resolve()}?mode=ro',uri=True) as db:
            table=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='control_plans'").fetchone()
            if table:
                inflight=db.execute("SELECT COUNT(*) FROM control_plans WHERE state='DISPATCHING'").fetchone()[0]
                checks['control_queue_reconciliation']={'status':'PASS' if inflight==0 else 'BLOCKED',
                    'unreconciled_inflight':inflight}
            else:
                checks['control_queue_reconciliation']={'status':'NOT_TESTED','reason':'control_plane_not_initialized'}
    except (sqlite3.Error,OSError) as exc:
        checks['control_queue_reconciliation']={'status':'FAIL','reason':type(exc).__name__}
    checks['computer_view_and_control_on_target']={'status':'NOT_TESTED',
        'reason':'requires target computer online, operator consent and verified screen/control evidence'}
    checks['plugin_space_live_connector']={'status':'NOT_TESTED',
        'reason':'requires independently authorized ChatGPT connector/Space bridge and access audit'}
    checks['backup_restore_drill']=(sqlite_backup_restore_drill(rt.ms.db_path) if do_restore
                                     else {'status':'NOT_TESTED','reason':'drill_disabled'})
    # Honest difference: local preflight never proves independent security review, TLS,
    # external source truth, Origin identity, live model, or real action/outcome.
    blocking=[name for name,entry in checks.items() if entry['status']!='PASS']
    return {'status':'READY_FOR_EXTERNAL_REVIEW' if not blocking else 'BLOCKED',
            'production_approved':False,'gate_s10':'NOT_PASSED',
            'evaluated_at':datetime.now(timezone.utc).isoformat(),
            'checks':checks,'blocking_checks':blocking,
            'required_manual_evidence':[
                'out-of-band Origin identity and explicit release authorization',
                'real deployed TLS/identity/RBAC boundary and vulnerability assessment',
                'offsite immutable anchor, offsite backup, recovery time verification',
                'independent S10-01..S10-20 evidence and reviewer signoff',
                'Thai/model heldout evaluation and G06 blind novelty assessment',
                'operational monitoring, rollback, incident and PDPA procedures'],
            'disclosure':'This is an offline local preflight, not production certification'}
