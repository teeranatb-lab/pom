"""G-06 trusted-template source code improvement with explicit signed per-patch approval.

This is a developer-machine workflow, not a secure container or an autonomous Origin.
No arbitrary model-created code is executed. Each allowlisted source edit is regenerated
and checked against original bytes, tested in a copied workspace, then requires BOTH
CANTI source_apply grant AND an independently signed one-shot approval bound to the
exact proposal/test digest. Backups are retained; multi-file OS replaces are NOT atomic
as a group, so on failures this module attempts to restore all files.
"""
from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,os,sqlite3,tempfile
from .gaps import GapDetector
from .proposals import ProposalGenerator,version_next,current_mapping,INTENT_TEMPLATES,ALLOWED_TARGETS,sha_bytes
from .sandbox import SandboxRunner,G06_REGRESSION_TARGETS


def _j(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def _sha(v):return hashlib.sha256(_j(v).encode()).hexdigest()
def _now():return datetime.now(timezone.utc).isoformat()

def approval_message(receipt):
    return b'OLGM-G06-SOURCE-MUTATION-v1\n'+_j(receipt).encode('utf-8')

@contextmanager
def exclusive_repo_lock(root):
    lock=Path(root)/'.olgm_g06.lock'
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        os.write(fd,str(os.getpid()).encode())
        yield
    finally:
        os.close(fd)
        try:lock.unlink()
        except FileNotFoundError:pass

class SourceImprover:
    def __init__(self,repo,db_path,audit,canti):
        self.repo=Path(repo).resolve();self.db=str(db_path);self.audit=audit;self.canti=canti
        if not (self.repo/'olgm/methods.py').is_file():raise ValueError('repo_missing_methods')
        with self._conn() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS g06_source_proposals (
                proposal_id TEXT PRIMARY KEY, payload TEXT NOT NULL, assessment TEXT NOT NULL,
                status TEXT NOT NULL, backup_dir TEXT, created_at TEXT NOT NULL,
                applied_at TEXT, changed_at TEXT);
                CREATE TABLE IF NOT EXISTS g06_source_nonces (
                nonce TEXT PRIMARY KEY, proposal_id TEXT NOT NULL, action TEXT NOT NULL, used_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS g06_source_meta (
                name TEXT PRIMARY KEY,value TEXT NOT NULL);
                INSERT OR IGNORE INTO g06_source_meta VALUES('version','0.7.0');''')
    def _conn(self):
        conn=sqlite3.connect(self.db,timeout=15)
        conn.row_factory=sqlite3.Row
        return conn
    def _version(self):
        with self._conn() as db:return db.execute("SELECT value FROM g06_source_meta WHERE name='version'").fetchone()['value']
    def status(self):
        with self._conn() as db:rows=db.execute('SELECT proposal_id,status,created_at,applied_at FROM g06_source_proposals ORDER BY created_at').fetchall()
        return {'version':self._version(),'proposals':[dict(x) for x in rows],
                'scope':'predefined_intent_routing_only','canonical_modified':False}

    def propose(self,intent):
        # No source mutation. The code generator is deliberately bounded to known safe templates.
        gap=GapDetector(self.repo).from_exception(ValueError(f'UnsupportedIntent: {intent}'))
        if not gap:return {'status':'INVALID_INTENT'}
        current=self._version()
        proposal=ProposalGenerator(self.repo).generate(gap,current)
        if not proposal:return {'status':'NO_TEMPLATE_OR_ALREADY_SUPPORTED','intent':intent}
        mapping,_=current_mapping((self.repo/'olgm/methods.py').read_text(encoding='utf-8'))
        assessment=SandboxRunner(self.repo).assess(proposal.to_dict(),mapping,INTENT_TEMPLATES[intent])
        payload=proposal.to_dict()
        state='AWAITING_SIGNED_APPROVAL' if assessment['ok'] else 'REJECTED_BY_REGRESSION'
        with self._conn() as db:
            db.execute('INSERT OR IGNORE INTO g06_source_proposals VALUES(?,?,?,?,?,?,?,?)',
                (proposal.proposal_id,_j(payload),_j(assessment),state,None,_now(),None,None))
        self.audit.append(proposal.proposal_id,'G06_CODE_PROPOSAL',
                {'fingerprint':proposal.fingerprint,'intent':intent,'assessment':assessment,'status':state})
        return {'status':state,'proposal_id':proposal.proposal_id,
                'fingerprint':proposal.fingerprint,'version_candidate':proposal.new_version,
                'diffs':[f.diff for f in proposal.files],'assessment':assessment,
                'notice':'No source change; sign a per-proposal receipt from an independently held key.'}

    def _get(self,pid):
        with self._conn() as db:
            row=db.execute('SELECT * FROM g06_source_proposals WHERE proposal_id=?',(pid,)).fetchone()
        if not row:raise ValueError('unknown_proposal')
        return dict(row),json.loads(row['payload']),json.loads(row['assessment'])

    def receipt_template(self,pid,principal,action='apply',expires_at=None,nonce=None):
        import uuid
        if action not in ('apply','rollback'):raise ValueError('invalid_action')
        row,proposal,assess=self._get(pid)
        expected='AWAITING_SIGNED_APPROVAL' if action=='apply' else 'APPLIED'
        if row['status']!=expected:raise ValueError('proposal_not_ready_for_action')
        if not expires_at:
            from datetime import timedelta
            expires_at=(datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat()
        return {'domain':'OLGM-G06-SOURCE-MUTATION-v1','proposal_id':pid,
                'fingerprint':proposal['fingerprint'],'assessment_sha256':_sha(assess),
                'principal':principal,'action':action,'resource':'repo.olgm.methods',
                'expires_at':expires_at,'nonce':nonce or str(uuid.uuid4())}

    def _authorize(self,receipt,signature,pid,action,proposal,assessment):
        if not self.canti.check('source_apply','repo.olgm.methods')['allowed']:
            raise PermissionError('CANTI_source_apply_grant_required')
        required={'domain','proposal_id','fingerprint','assessment_sha256','principal',
                  'action','resource','expires_at','nonce'}
        if not isinstance(receipt,dict) or set(receipt)!=required:
            raise PermissionError('invalid_receipt_fields')
        if receipt['domain']!='OLGM-G06-SOURCE-MUTATION-v1' or receipt['proposal_id']!=pid or \
           receipt['action']!=action or receipt['fingerprint']!=proposal['fingerprint'] or \
           receipt['assessment_sha256']!=_sha(assessment) or receipt['resource']!='repo.olgm.methods':
            raise PermissionError('receipt_scope_or_patch_mismatch')
        expiry=datetime.fromisoformat(receipt['expires_at'])
        if expiry.tzinfo is None or datetime.now(timezone.utc)>=expiry:
            raise PermissionError('receipt_expired')
        with self._conn() as db:
            key=db.execute('SELECT public_key_hex,authority FROM trusted_public_keys WHERE principal=? AND revoked_at IS NULL',
                           (receipt['principal'],)).fetchone()
            seen=db.execute('SELECT 1 FROM g06_source_nonces WHERE nonce=?',(receipt['nonce'],)).fetchone()
        if not key or key['authority']!='Origin':raise PermissionError('origin_key_not_enrolled')
        if seen:raise PermissionError('approval_nonce_replay')
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(key['public_key_hex'])).verify(
                bytes.fromhex(signature),approval_message(receipt))
        except Exception as exc:raise PermissionError('approval_signature_invalid') from exc
        return {'principal':receipt['principal'],'receipt_digest':_sha(receipt),'nonce':receipt['nonce']}

    def _replace(self,path,data):
        # Within-filesystem atomic replacement of one file, NOT atomic across multiple files.
        fd,tmp=tempfile.mkstemp(prefix='.g06_new_',dir=path.parent)
        try:
            with os.fdopen(fd,'wb') as f:
                f.write(data);f.flush();os.fsync(f.fileno())
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)

    def apply(self,pid,receipt,signature):
        with exclusive_repo_lock(self.repo):
            row,p,assessment=self._get(pid)
            if row['status']!='AWAITING_SIGNED_APPROVAL' or not assessment['ok']:
                raise PermissionError('proposal_not_approved_ready')
            auth=self._authorize(receipt,signature,pid,'apply',p,assessment)
            expected=ProposalGenerator(self.repo).validate(p)
            if set(f['path'] for f in p['files'])!=ALLOWED_TARGETS:
                raise PermissionError('invalid_target_set')
            for f in p['files']:
                target=(self.repo/f['path']).resolve()
                if not target.is_relative_to(self.repo) or target.is_symlink():raise PermissionError('path_escape')
                actual=sha_bytes(target.read_bytes()) if target.exists() else None
                if actual!=f['old_sha256']:raise PermissionError('source_changed_since_proposal')
                if sha_bytes(f['patched_text'].encode())!=f['new_sha256']:raise PermissionError('patched_hash_mismatch')
            backup=self.repo/'.g06_backups'/pid
            if backup.exists():raise PermissionError('backup_already_exists')
            backup.mkdir(parents=True)
            originals={}
            try:
                for f in p['files']:
                    originals[f['path']]=(self.repo/f['path']).read_bytes() if f['old_sha256'] else None
                    dest=backup/f['path'];dest.parent.mkdir(parents=True,exist_ok=True)
                    if originals[f['path']] is not None:dest.write_bytes(originals[f['path']])
                # Safety journal, retain immutable backup until explicit rollback.
                (backup/'metadata.json').write_text(_j({'proposal':pid,
                   'files':{k:(sha_bytes(v) if v is not None else None) for k,v in originals.items()}}))
                for f in p['files']:
                    path=self.repo/f['path'];path.parent.mkdir(parents=True,exist_ok=True)
                    self._replace(path,f['patched_text'].encode('utf-8'))
                # Independent process import proof; full test suite is already run on trusted copy.
                post=SandboxRunner(self.repo)._run([
                     __import__('sys').executable,'-m','pytest','-q','-ra',*G06_REGRESSION_TARGETS],self.repo)
                if not post['ok']:raise RuntimeError('post_apply_regression:'+post['output_tail'][-300:])
                with self._conn() as db:
                    db.execute('BEGIN IMMEDIATE')
                    db.execute('INSERT INTO g06_source_nonces VALUES(?,?,?,?)',
                         (auth['nonce'],pid,'apply',_now()))
                    db.execute('UPDATE g06_source_proposals SET status=?,backup_dir=?,applied_at=?,changed_at=? WHERE proposal_id=?',
                               ('APPLIED',str(backup),_now(),_now(),pid))
                    db.execute("UPDATE g06_source_meta SET value=? WHERE name='version'",(p['new_version'],))
                self.audit.append(pid,'G06_CODE_APPLIED',{'fingerprint':p['fingerprint'],
                        'receipt_digest':auth['receipt_digest'],'post_test':post,'version':p['new_version']})
                return {'status':'APPLIED','version':p['new_version'],'post_test':post,
                        'backup_retained':str(backup),'note':'template-based intent routing only'}
            except Exception as exc:
                for relative,data in originals.items():
                    target=self.repo/relative
                    if data is None:
                        if target.exists():target.unlink()
                    else:self._replace(target,data)
                self.audit.append(pid,'G06_APPLY_ROLLED_BACK',{'reason':str(exc)[:200]})
                return {'status':'ROLLED_BACK','reason':str(exc)[:350]}

    def rollback(self,pid,receipt,signature):
        with exclusive_repo_lock(self.repo):
            row,p,assessment=self._get(pid)
            if row['status']!='APPLIED':raise PermissionError('not_applied')
            auth=self._authorize(receipt,signature,pid,'rollback',p,assessment)
            backup=Path(row['backup_dir']).resolve()
            if not backup.is_relative_to(self.repo/'.g06_backups') or not backup.is_dir():
                raise PermissionError('bad_backup_dir')
            # Refuse rollback if another actor changed source after apply.
            for f in p['files']:
                target=self.repo/f['path']
                if not target.exists() or sha_bytes(target.read_bytes())!=f['new_sha256']:
                    raise PermissionError('source_changed_since_apply')
            originals={}
            for f in p['files']:
                original=None if f['old_sha256'] is None else (backup/f['path']).read_bytes()
                if original is not None and sha_bytes(original)!=f['old_sha256']:
                    raise PermissionError('backup_integrity_failed')
                originals[f['path']]=original
            for relative,original in originals.items():
                target=self.repo/relative
                if original is None:target.unlink()
                else:self._replace(target,original)
            version=version_next(self._version())
            with self._conn() as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('INSERT INTO g06_source_nonces VALUES(?,?,?,?)',
                           (auth['nonce'],pid,'rollback',_now()))
                db.execute('UPDATE g06_source_proposals SET status=?,changed_at=? WHERE proposal_id=?',
                           ('ROLLED_BACK',_now(),pid))
                db.execute("UPDATE g06_source_meta SET value=? WHERE name='version'",(version,))
            self.audit.append(pid,'G06_EXPLICIT_ROLLBACK',{'version':version,
                 'receipt_digest':auth['receipt_digest']})
            return {'status':'ROLLED_BACK','version':version,'historical_record_preserved':True}
