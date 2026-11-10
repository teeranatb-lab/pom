"""Multimodal provenance and safe metadata ingest (NOT vision/audio understanding).
No cloud upload, model calls or live meaning mutation.
"""
import hashlib
import mimetypes
import os
import sqlite3
import uuid
from pathlib import Path
from .intent import now

ACCEPTED={'text/plain','text/csv','image/png','image/jpeg','image/webp',
          'audio/wav','audio/x-wav','application/pdf','video/mp4'}


class MultimodalIngest:
    def __init__(self,db_path):
        self.db_path=str(db_path)
        with self._db() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS media_assets (
                asset_id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, media_type TEXT NOT NULL,
                bytes INTEGER NOT NULL, original_name TEXT NOT NULL,
                origin_ref TEXT NOT NULL, created_at TEXT NOT NULL,
                parse_status TEXT NOT NULL, metadata_json TEXT NOT NULL)''')

    def _db(self):return sqlite3.connect(self.db_path,timeout=15)

    def ingest(self,path,origin_ref, max_bytes=20*1024*1024):
        import json
        file=Path(path)
        if not origin_ref:raise ValueError('origin_ref required')
        if not file.is_file() or file.is_symlink():raise ValueError('regular non-symlink file required')
        if file.stat().st_size>max_bytes:raise ValueError('file exceeds configured size limit')
        kind=mimetypes.guess_type(str(file))[0]
        if kind not in ACCEPTED:raise ValueError('unsupported media type')
        h=hashlib.sha256();size=0
        with file.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):
                h.update(chunk);size+=len(chunk)
        meta={'filename':file.name,'media_type':kind}
        status='HASHED_METADATA_ONLY'
        if kind.startswith('image/'):
            try:
                from PIL import Image
                with Image.open(file) as im:
                    im.verify()
                with Image.open(file) as im:
                    meta['pixels']=list(im.size)
                status='IMAGE_METADATA_EXTRACTED_VISION_NOT_TESTED'
            except ImportError:status='IMAGE_METADATA_NOT_TESTED'
        elif kind in ('audio/wav','audio/x-wav'):
            import wave
            with wave.open(str(file),'rb') as wav:
                meta.update({'duration_seconds':wav.getnframes()/wav.getframerate(),
                             'sample_rate':wav.getframerate(),'channels':wav.getnchannels()})
            status='AUDIO_METADATA_EXTRACTED_TRANSCRIPTION_NOT_TESTED'
        elif kind=='text/plain':
            try:
                with file.open(encoding='utf-8') as f:
                    meta['text_preview']=f.read(256)
                status='TEXT_PREVIEW_ONLY'
            except UnicodeError:status='TEXT_ENCODING_NOT_TESTED'
        aid=str(uuid.uuid4())
        with self._db() as db:
            db.execute('INSERT INTO media_assets VALUES(?,?,?,?,?,?,?,?,?)',
                       (aid,h.hexdigest(),kind,size,file.name,origin_ref,now(),status,
                        json.dumps(meta,ensure_ascii=False)))
        return {'status':status,'asset_id':aid,'sha256':h.hexdigest(),
                'bytes':size,'metadata':meta,'semantic_interpretation':'NOT_TESTED'}
