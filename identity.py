"""Optional public-key authorization receipts (Ed25519); private keys NEVER stored.

Key enrollment is an explicit trusted local bootstrap step. It does not prove an
actor is the real Origin by itself; out-of-band identity vetting is mandatory.
"""
import json
import sqlite3
from datetime import datetime,timezone
from .intent import digest,now

REQUIRED=('principal','plan_id','intent_id','intent_hash','resource','scope','nonce',
          'expires_at','approval_ref','decision_ref')


class SignedAuthorizations:
    def __init__(self,db_path):
        self.db_path=str(db_path)
        with self._db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS trusted_public_keys (
                    principal TEXT PRIMARY KEY,public_key_hex TEXT NOT NULL,
                    authority TEXT NOT NULL, enrolled_by TEXT NOT NULL,
                    enrolled_at TEXT NOT NULL,revoked_at TEXT);
                CREATE TABLE IF NOT EXISTS signed_auth_consumptions (
                    nonce TEXT PRIMARY KEY,principal TEXT NOT NULL,
                    receipt_hash TEXT NOT NULL,consumed_at TEXT NOT NULL);
            ''')

    def _db(self):
        db=sqlite3.connect(self.db_path,timeout=15);db.row_factory=sqlite3.Row;return db

    def enroll_public_key(self,principal,public_key_hex,authority,enrolled_by):
        """Local trust bootstrap. No remote unauthenticated enrollment route."""
        if not principal or not enrolled_by or authority not in ('Origin','approver','reviewer'):
            raise ValueError('actor, authority and enroller required')
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            key=Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        except (ImportError,ValueError) as exc:
            raise ValueError('invalid Ed25519 public key') from exc
        with self._db() as db:
            db.execute('INSERT INTO trusted_public_keys VALUES(?,?,?,?,?,NULL)',
                       (principal,public_key_hex,authority,enrolled_by,now()))
        return {'status':'KEY_ENROLLED_LOCAL_TRUST_BOOTSTRAP','principal':principal,
                'identity_authenticity':'NOT_INDEPENDENTLY_VERIFIED'}

    def verify(self,receipt,signature_hex,expected_plan_id=None,expected_resource=None,consume=False):
        if not isinstance(receipt,dict) or any(not receipt.get(x) for x in REQUIRED):
            return {'status':'DENIED','reason':'missing_receipt_fields'}
        if expected_plan_id and receipt['plan_id']!=expected_plan_id:
            return {'status':'DENIED','reason':'plan_not_bound'}
        if expected_resource and receipt['resource']!=expected_resource:
            return {'status':'DENIED','reason':'scope_not_bound'}
        if receipt['scope']!='sandbox_write':
            return {'status':'DENIED','reason':'scope_invalid'}
        try:
            exp=datetime.fromisoformat(receipt['expires_at'])
            if exp.tzinfo is None or exp<=datetime.now(timezone.utc):
                return {'status':'DENIED','reason':'expired_or_naive_expiry'}
        except (TypeError,ValueError):
            return {'status':'DENIED','reason':'bad_expiry'}
        with self._db() as db:
            row=db.execute('SELECT * FROM trusted_public_keys WHERE principal=? AND revoked_at IS NULL',
                           (receipt['principal'],)).fetchone()
            seen=db.execute('SELECT 1 FROM signed_auth_consumptions WHERE nonce=?',
                            (receipt['nonce'],)).fetchone()
        if not row:return {'status':'DENIED','reason':'unknown_or_revoked_public_key'}
        if row['authority'] not in ('Origin','approver'):
            return {'status':'DENIED','reason':'actor_not_approver'}
        if seen:return {'status':'DENIED','reason':'nonce_replay'}
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            from cryptography.exceptions import InvalidSignature
            key=Ed25519PublicKey.from_public_bytes(bytes.fromhex(row['public_key_hex']))
            key.verify(bytes.fromhex(signature_hex),digest(receipt).encode())
        except (ImportError,InvalidSignature,ValueError,TypeError):
            return {'status':'DENIED','reason':'signature_invalid'}
        if consume:
            try:
                with self._db() as db:
                    db.execute('INSERT INTO signed_auth_consumptions VALUES(?,?,?,?)',
                               (receipt['nonce'],receipt['principal'],digest(receipt),now()))
            except sqlite3.IntegrityError:
                return {'status':'DENIED','reason':'nonce_replay'}
        return {'status':'VERIFIED_SIGNATURE' if not consume else 'CONSUMED_SIGNATURE',
                'principal':receipt['principal'],'authority':row['authority'],
                'receipt_hash':digest(receipt),
                'caution':'Key ownership is established only to extent of local trusted enrollment'}
