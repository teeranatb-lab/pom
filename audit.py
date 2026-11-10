"""Local hash chain and optional independently keyed file anchors.

A local file is NOT a trustworthy external service. Store anchor copy and key outside
this host for stronger anti-rollback guarantees.
"""
import hashlib
import hmac
import json
import os
import sqlite3
from datetime import datetime, timezone


def _json(d):
    return json.dumps(d, sort_keys=True, ensure_ascii=False, separators=(',', ':'))


def _sha(d):
    return hashlib.sha256(_json(d).encode('utf-8')).hexdigest()


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


class AuditChain:
    def __init__(self, db_path, external_anchor_path=None, anchor_key=None):
        self.db_path = str(db_path)
        self.external_anchor_path = str(external_anchor_path) if external_anchor_path else None
        self.anchor_key = anchor_key.encode() if isinstance(anchor_key, str) else anchor_key
        with self._conn() as db:
            db.executescript('''
              CREATE TABLE IF NOT EXISTS audit_chain (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL, event_type TEXT NOT NULL, payload TEXT NOT NULL,
                prev_hash TEXT NOT NULL, self_hash TEXT NOT NULL, created_at TEXT NOT NULL
              );
              CREATE TABLE IF NOT EXISTS audit_anchors (
                anchor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                chain_seq INTEGER NOT NULL, chain_hash TEXT NOT NULL,
                external_ref TEXT NOT NULL, created_at TEXT NOT NULL, signature TEXT,
                FOREIGN KEY(chain_seq) REFERENCES audit_chain(seq)
              );
            ''')

    def _conn(self):
        db = sqlite3.connect(self.db_path, timeout=15)
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA busy_timeout=15000')
        return db

    @staticmethod
    def _digest(seq, trace_id, event_type, payload, prev_hash, created_at):
        return _sha({'domain':'olgm:audit:v2', 'seq':seq, 'trace_id':trace_id,
                     'event_type':event_type, 'payload':payload,
                     'prev_hash':prev_hash, 'created_at':created_at})

    def append(self, trace_id, event_type, payload):
        pj = _json(payload)
        now = _utcnow()
        with self._conn() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT seq,self_hash FROM audit_chain ORDER BY seq DESC LIMIT 1').fetchone()
            seq = row[0]+1 if row else 1
            prev = row[1] if row else '0'*64
            digest = self._digest(seq, trace_id, event_type, pj, prev, now)
            db.execute('INSERT INTO audit_chain(seq,trace_id,event_type,payload,prev_hash,self_hash,created_at) VALUES (?,?,?,?,?,?,?)',
                       (seq,trace_id,event_type,pj,prev,digest,now))
        return seq, digest

    def anchor(self, external_ref):
        if not self.external_anchor_path:
            return {'status':'NOT_ANCHORED', 'reason':'external_anchor_path_not_configured'}
        with self._conn() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT seq,self_hash FROM audit_chain ORDER BY seq DESC LIMIT 1').fetchone()
            if not row:
                return {'status':'NOT_ANCHORED','reason':'empty_chain'}
            seq, ch = row
            entry = {'chain_seq':seq,'chain_hash':ch,'external_ref':external_ref,'created_at':_utcnow()}
            entry['signature'] = hmac.new(self.anchor_key, _json(entry).encode(), 'sha256').hexdigest() if self.anchor_key else None
            db.execute('INSERT INTO audit_anchors(chain_seq,chain_hash,external_ref,created_at,signature) VALUES(?,?,?,?,?)',
                       (entry['chain_seq'],entry['chain_hash'],entry['external_ref'],entry['created_at'],entry['signature']))
            # file before commit. Crash may leave dangling file entry; verification reports mismatch.
            fd = os.open(self.external_anchor_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            with os.fdopen(fd, 'a', encoding='utf-8') as f:
                f.write(_json(entry)+'\n')
                f.flush()
                os.fsync(f.fileno())
        return {'status': 'ANCHOR_RECORDED_LOCAL', 'chain_seq':seq,
                'signed':bool(self.anchor_key)}

    def verify(self):
        with self._conn() as db:
            rows = db.execute('SELECT seq,trace_id,event_type,payload,prev_hash,self_hash,created_at FROM audit_chain ORDER BY seq').fetchall()
            anchors = db.execute('SELECT chain_seq,chain_hash,external_ref,created_at,signature FROM audit_anchors ORDER BY anchor_id').fetchall()
        prev = '0'*64
        chain_by_seq = {}
        for expected, (seq, tid, et, pj, sp, sh, created) in enumerate(rows,1):
            if seq != expected:
                return False, f'sequence gap at {expected}'
            if sp != prev:
                return False, f'chain break at {seq}'
            if self._digest(seq,tid,et,pj,sp,created) != sh:
                return False, f'hash mismatch at {seq}'
            chain_by_seq[seq] = sh
            prev = sh
        for seq,ch,*_ in anchors:
            if chain_by_seq.get(seq) != ch:
                return False, f'anchor mismatch at {seq}'
        if self.external_anchor_path:
            if not os.path.isfile(self.external_anchor_path) and anchors:
                return False, 'external anchor file missing'
            try:
                with open(self.external_anchor_path, encoding='utf-8') as f:
                    file_anchors = [json.loads(x) for x in f if x.strip()]
            except FileNotFoundError:
                file_anchors = []
            except Exception as exc:
                return False, f'anchor file invalid: {exc}'
            db_anchors = [dict(chain_seq=s,chain_hash=c,external_ref=r,created_at=t,signature=sig)
                          for s,c,r,t,sig in anchors]
            if file_anchors != db_anchors:
                return False, 'anchor file and database differ'
            if self.anchor_key:
                for a in file_anchors:
                    sig = a.pop('signature', None)
                    expected_sig = hmac.new(self.anchor_key,_json(a).encode(),'sha256').hexdigest()
                    if not sig or not hmac.compare_digest(sig, expected_sig):
                        return False, f'anchor signature invalid at {a["chain_seq"]}'
        return True, f'OK ({len(rows)} records; {len(anchors)} local anchors)'
