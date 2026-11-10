"""SQLite Meaning Space with stable IDs, revision history, and category independence."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc).isoformat()


class MeaningSpace:
    def __init__(self, db_path):
        self.db_path = str(db_path)
        with self._conn() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS meaning_cores (
                cid TEXT PRIMARY KEY,
                language TEXT NOT NULL,
                surface_form TEXT NOT NULL,
                word_type TEXT,
                definition TEXT,
                sense_notes TEXT NOT NULL DEFAULT '',
                source_ref TEXT,
                semantic_coordinates TEXT,
                origin_ref TEXT,
                revision INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                UNIQUE(language, surface_form, sense_notes)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS meaning_cores_unique_coordinates
                ON meaning_cores(semantic_coordinates)
                WHERE semantic_coordinates IS NOT NULL;
            CREATE TABLE IF NOT EXISTS core_revisions (
                cid TEXT NOT NULL,
                revision INTEGER NOT NULL,
                snapshot TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(cid, revision),
                FOREIGN KEY(cid) REFERENCES meaning_cores(cid)
            );
            CREATE TABLE IF NOT EXISTS semantic_edges (
                edge_id TEXT PRIMARY KEY,
                source_cid TEXT NOT NULL,
                target_cid TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                direction TEXT NOT NULL DEFAULT 'forward',
                context TEXT,
                temporal_validity TEXT,
                constraints TEXT,
                evidence_ref TEXT,
                verification_status TEXT NOT NULL DEFAULT 'candidate',
                provenance TEXT,
                origin_ref TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(source_cid) REFERENCES meaning_cores(cid),
                FOREIGN KEY(target_cid) REFERENCES meaning_cores(cid)
            );
            CREATE TABLE IF NOT EXISTS evidence (
                evidence_ref TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_url TEXT,
                license TEXT,
                retrieved_at TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                excerpt TEXT
            );
            CREATE TABLE IF NOT EXISTS category_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cid TEXT NOT NULL,
                category TEXT NOT NULL,
                operation TEXT NOT NULL CHECK(operation IN ('assign','remove')),
                changed_at TEXT NOT NULL,
                reason TEXT NOT NULL,
                FOREIGN KEY(cid) REFERENCES meaning_cores(cid)
            );
            ''')

    def _conn(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def _one(self, sql, args):
        with self._conn() as db:
            row = db.execute(sql, args).fetchone()
        return dict(row) if row else None

    def add_core(self, cid, language, surface_form, definition=None, source_ref=None,
                 word_type=None, sense_notes='', coords=None, origin_ref=None):
        """Insert only. An existing core is never silently replaced."""
        if not (cid and language and surface_form and origin_ref):
            raise ValueError('cid, language, surface_form, and origin_ref are required')
        if coords is not None:
            if (not isinstance(coords, (list, tuple)) or len(coords) != 3
                    or any(type(v) not in (int, float) for v in coords)):
                raise ValueError('coords must be three numeric dimensions (x, y, z)')
            coords_json = json.dumps([float(v) for v in coords], separators=(',', ':'), allow_nan=False)
        else:
            coords_json = None
        now = utcnow()
        with self._conn() as db:
            db.execute('''INSERT INTO meaning_cores
                (cid, language, surface_form, word_type, definition, sense_notes,
                 source_ref, semantic_coordinates, origin_ref, revision, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                (cid, language, surface_form, word_type, definition, sense_notes or '',
                 source_ref, coords_json, origin_ref, 1, now))
            row = db.execute('SELECT * FROM meaning_cores WHERE cid=?', (cid,)).fetchone()
            db.execute('INSERT INTO core_revisions VALUES (?,?,?,?,?)',
                       (cid, 1, json.dumps(dict(row), ensure_ascii=False, sort_keys=True), 'created', now))
        return cid

    def revise_core(self, cid, *, definition, reason):
        """Append snapshot on revision; CID and edges remain stable."""
        if not reason:
            raise ValueError('revision reason required')
        with self._conn() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM meaning_cores WHERE cid=?', (cid,)).fetchone()
            if row is None:
                raise KeyError(cid)
            revision = row['revision'] + 1
            db.execute('UPDATE meaning_cores SET definition=?, revision=? WHERE cid=?',
                       (definition, revision, cid))
            row = db.execute('SELECT * FROM meaning_cores WHERE cid=?', (cid,)).fetchone()
            db.execute('INSERT INTO core_revisions VALUES (?,?,?,?,?)',
                       (cid, revision, json.dumps(dict(row), ensure_ascii=False, sort_keys=True),
                        reason, utcnow()))
        return revision

    def assign_category(self, cid, category, reason, operation='assign'):
        if not self.get_core(cid):
            raise KeyError(cid)
        if not reason or not category:
            raise ValueError('category and reason are required')
        with self._conn() as db:
            db.execute('INSERT INTO category_events(cid,category,operation,changed_at,reason) VALUES(?,?,?,?,?)',
                       (cid, category, operation, utcnow(), reason))

    def get_categories(self, cid):
        with self._conn() as db:
            rows = db.execute('SELECT category,operation FROM category_events WHERE cid=? ORDER BY event_id', (cid,)).fetchall()
        active = set()
        for row in rows:
            (active.add if row['operation'] == 'assign' else active.discard)(row['category'])
        return sorted(active)

    def add_edge(self, edge_id, source_cid, target_cid, relation_type,
                 context=None, evidence_ref=None, provenance=None, origin_ref=None):
        if not all([edge_id, source_cid, target_cid, relation_type, origin_ref]):
            raise ValueError('edge_id, source_cid, target_cid, relation_type, origin_ref required')
        with self._conn() as db:
            db.execute('''INSERT INTO semantic_edges
                (edge_id, source_cid, target_cid, relation_type, context, evidence_ref,
                 provenance, origin_ref, created_at)
                 VALUES (?,?,?,?,?,?,?,?,?)''',
                 (edge_id, source_cid, target_cid, relation_type, context,
                  evidence_ref, provenance, origin_ref, utcnow()))
        return edge_id

    def add_evidence(self, evidence_ref, source_type, content, source_url=None, license=None):
        if not isinstance(content, (str, bytes)) or not content:
            raise ValueError('nonempty evidence content required')
        content_bytes = content.encode('utf-8') if isinstance(content, str) else content
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        with self._conn() as db:
            db.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?)',
                       (evidence_ref, source_type, source_url, license, utcnow(),
                        content_hash, content if isinstance(content, str) else None))
        return evidence_ref

    def get_core(self, cid):
        return self._one('SELECT * FROM meaning_cores WHERE cid=?', (cid,))

    def get_edge(self, eid):
        return self._one('SELECT * FROM semantic_edges WHERE edge_id=?', (eid,))

    def get_evidence(self, ref):
        return self._one('SELECT * FROM evidence WHERE evidence_ref=?', (ref,))

    def context_snapshot(self, cids, limit=30):
        if not cids:
            return []
        limit = max(1, min(int(limit), 100))
        cids = list(dict.fromkeys(cids))[:limit]
        placeholders = ','.join('?' for _ in cids)
        with self._conn() as db:
            rows = db.execute(f'SELECT cid,surface_form,definition,origin_ref FROM meaning_cores WHERE cid IN ({placeholders}) LIMIT ?',
                              (*cids, limit)).fetchall()
        return [dict(r) for r in rows]
