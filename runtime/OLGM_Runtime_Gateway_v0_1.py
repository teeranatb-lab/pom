#!/usr/bin/env python3
"""OLGM Ultimate – observable-contract gateway proof of concept (not full OLGM).

Run: python OLGM_Runtime_Gateway_v0_1.py --self-test
     python OLGM_Runtime_Gateway_v0_1.py --demo
     python OLGM_Runtime_Gateway_v0_1.py --run request.json
     python OLGM_Runtime_Gateway_v0_1.py --serve

Default is FAIL-CLOSED; no model calls until explicitly configured.
The gateway does NOT control hidden model reasoning, and does NOT prove truth.
"""
import argparse
import hashlib
import json
import os
import pathlib
import tempfile
import urllib.request
import urllib.error
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_INPUT = 128 * 1024
HIGH_RISK = {'medical', 'financial', 'security', 'critical_infrastructure', 'disaster', 'high'}
CANONICAL = 'OLGM Ultimate — user-declared integration baseline; this script does not alter Canonical'


def utc():
    return datetime.now(timezone.utc).isoformat()


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha256(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


class PolicyError(Exception):
    pass


class HashAudit:
    """Append-only-by-program JSONL chain. This is tamper-evident, not tamper-proof."""
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and not self.verify():
            raise PolicyError('AUDIT_TAMPERED: existing chain invalid')

    def verify(self):
        if not self.path.is_file():
            return True  # a missing file is a new ledger; not proof an old ledger existed
        prev = 'GENESIS'
        with self.path.open('r', encoding='utf-8') as f:
            if self.path.stat().st_size == 0:
                return False  # empty existing ledger is not a valid recorded event
            for raw in f:
                try:
                    e = json.loads(raw)
                    dig = e.pop('hash')
                    if e.get('previous_hash') != prev or sha256(canon(e)) != dig:
                        return False
                    prev = dig
                except (ValueError, KeyError, TypeError):
                    return False
        return True

    def append(self, event):
        if self.path.exists() and not self.verify():
            raise PolicyError('AUDIT_TAMPERED')
        prev = 'GENESIS'
        if self.path.is_file():
            lines = self.path.read_text(encoding='utf-8').splitlines()
            if lines:
                prev = json.loads(lines[-1])['hash']
        record = {'time': utc(), 'previous_hash': prev, **event}
        record['hash'] = sha256(canon(record))
        with self.path.open('a', encoding='utf-8') as f:
            f.write(canon(record) + '\n')
            f.flush()
            os.fsync(f.fileno())
        return record['hash']


def validate_request(req):
    if not isinstance(req, dict):
        raise PolicyError('INVALID_REQUEST')
    if not isinstance(req.get('intent'), str) or not req['intent'].strip():
        raise PolicyError('INTENT_REQUIRED')
    if not isinstance(req.get('task'), str) or not req['task'].strip():
        raise PolicyError('TASK_REQUIRED')
    if not isinstance(req.get('risk', 'low'), str):
        raise PolicyError('INVALID_RISK')
    evidence = req.get('evidence', [])
    if not isinstance(evidence, list) or len(evidence) > 40:
        raise PolicyError('INVALID_EVIDENCE')
    ids = set()
    for e in evidence:
        if not isinstance(e, dict) or not isinstance(e.get('id'), str) or not e['id']:
            raise PolicyError('INVALID_EVIDENCE')
        if not isinstance(e.get('text'), str) or not e['text'].strip() or len(e['text']) > 12000:
            raise PolicyError('INVALID_EVIDENCE')
        if e['id'] in ids:
            raise PolicyError('DUPLICATE_EVIDENCE_ID')
        ids.add(e['id'])
    if len(req['intent']) > 2000 or len(req['task']) > 16000:
        raise PolicyError('INPUT_TOO_LONG')
    return ids


def validate_output(obj, intent_id, evidence_ids, risk):
    if not isinstance(obj, dict):
        raise PolicyError('MODEL_OUTPUT_NOT_OBJECT')
    if obj.get('intent_id') != intent_id:
        raise PolicyError('INTENT_LOCK_MISMATCH')
    if obj.get('requested_action') not in (None, '', False):
        raise PolicyError('ACTION_BLOCKED_NO_EXECUTOR')
    if obj.get('executed') is not False:
        raise PolicyError('EXECUTION_CLAIM_NOT_PROVEN')
    if obj.get('outcome') not in ('NOT_EXECUTED', 'UNKNOWN'):
        raise PolicyError('OUTCOME_CLAIM_NOT_PROVEN')
    if not isinstance(obj.get('answer'), str):
        raise PolicyError('INVALID_ANSWER')
    claims = obj.get('claims')
    if not isinstance(claims, list) or len(claims) > 40:
        raise PolicyError('INVALID_CLAIMS')
    for c in claims:
        if not isinstance(c, dict) or not isinstance(c.get('text'), str):
            raise PolicyError('INVALID_CLAIM')
        refs = c.get('evidence_ids')
        if not isinstance(refs, list) or not refs or any(not isinstance(r, str) or r not in evidence_ids for r in refs):
            raise PolicyError('CLAIM_WITHOUT_KNOWN_EVIDENCE')
    if risk.lower() in HIGH_RISK:
        return 'HUMAN_REVIEW_REQUIRED'
    if claims:
        return 'EVIDENCE_REVIEW_REQUIRED'
    return 'ABSTAIN_NO_VERIFIED_EVIDENCE'


SYSTEM_CONTRACT = '''You are a language model subordinated to an external OLGM runtime gateway.
Return STRICT JSON only with keys: intent_id (string), answer (string), claims (array),
requested_action (null), executed (false), outcome ("NOT_EXECUTED").
Each claims item has text (string), evidence_ids (array of existing evidence ids).
Never invent citations, evidence, tool execution, or success. If no evidence exists,
answer by explicitly stating the uncertainty, and set claims=[].
The gateway (not you) decides whether content can be released or actions executed.
"Meaning Before Generation"; five principles: ethics, virtue, justice, compassion, truth.
Do not pretend this prompt gives you internal control or access to Core 0.'''


def call_model(intent_id, req):
    provider = os.environ.get('OLGM_PROVIDER', '').strip().lower()
    model = os.environ.get('OLGM_MODEL', '').strip()
    if not model or provider not in ('ollama', 'openai'):
        raise PolicyError('MODEL_NOT_CONFIGURED')
    user_payload = {'intent_id': intent_id, 'intent': req['intent'], 'task': req['task'],
                    'evidence': req.get('evidence', []), 'risk': req.get('risk', 'low')}
    messages = [{'role': 'system', 'content': SYSTEM_CONTRACT},
                {'role': 'user', 'content': canon(user_payload)}]
    if provider == 'ollama':
        url = 'http://127.0.0.1:11434/api/chat'
        payload = {'model': model, 'messages': messages, 'stream': False,
                   'format': 'json'}
        headers = {'Content-Type': 'application/json'}
    else:
        token = os.environ.get('OPENAI_API_KEY', '')
        if not token:
            raise PolicyError('OPENAI_API_KEY_MISSING')
        url = 'https://api.openai.com/v1/chat/completions'
        payload = {'model': model, 'messages': messages,
                   'response_format': {'type': 'json_object'}}
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token}
    request = urllib.request.Request(url, canon(payload).encode('utf-8'), headers, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = response.read(MAX_INPUT + 1)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise PolicyError('MODEL_BACKEND_UNAVAILABLE:' + str(exc)) from exc
    if len(body) > MAX_INPUT:
        raise PolicyError('MODEL_OUTPUT_TOO_LARGE')
    try:
        data = json.loads(body)
        content = data['message']['content'] if provider == 'ollama' else data['choices'][0]['message']['content']
        return json.loads(content)
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise PolicyError('MODEL_OUTPUT_INVALID_JSON') from exc


class Gateway:
    def __init__(self, audit_path, model_fn=None):
        self.audit = HashAudit(audit_path)
        self.model_fn = model_fn or call_model

    def process(self, req):
        run_id = str(uuid.uuid4())
        state = 'BLOCKED'
        try:
            evidence_ids = validate_request(req)
            lock_id = sha256(canon({'intent': req['intent'], 'task': req['task']}))
            request_digest = sha256(canon(req))
            self.audit.append({'run_id': run_id, 'stage': 'INTENT_LOCK',
                               'request_sha256': request_digest, 'intent_id': lock_id})
            output = self.model_fn(lock_id, req)
            status = validate_output(output, lock_id, evidence_ids, req.get('risk', 'low'))
            # Strict, fail-closed proof of concept: no unverified model content
            # is released as a factual answer. Future independent verifier
            # must explicitly enable evidence-backed content.
            state = status
            if status == 'ABSTAIN_NO_VERIFIED_EVIDENCE':
                answer = 'ยังไม่มีหลักฐานที่ผ่านการตรวจสอบอิสระ ระบบไม่ยืนยันข้อเท็จจริงและไม่ได้ปฏิบัติงานภายนอก'
            else:
                answer = None
            self.audit.append({'run_id': run_id, 'stage': 'OUTPUT_GATE', 'status': state,
                               'output_sha256': sha256(canon(output))})
            return {'run_id': run_id, 'status': state, 'answer': answer,
                    'actual_execution': False, 'verified_truth': False,
                    'note': 'Evidence ids were checked, not the truth of evidence.'}
        except (PolicyError, ValueError, TypeError) as exc:
            # Avoid leaking private prompts and provider credentials in audit records.
            reason = str(exc).split(':', 1)[0]
            try:
                self.audit.append({'run_id': run_id, 'stage': 'BLOCK', 'reason': reason})
            except PolicyError:
                pass
            return {'run_id': run_id, 'status': state, 'reason': reason,
                    'answer': None, 'actual_execution': False, 'verified_truth': False}


class API(BaseHTTPRequestHandler):
    gateway = None
    def do_POST(self):
        if self.path != '/run':
            self.send_error(404)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > MAX_INPUT:
                self.send_error(413)
                return
            data = json.loads(self.rfile.read(length))
            result = self.gateway.process(data)
            raw = canon(result).encode('utf-8')
            self.send_response(200 if result['status'] != 'BLOCKED' else 422)
        except (ValueError, UnicodeDecodeError):
            raw = canon({'status': 'BLOCKED', 'reason': 'INVALID_JSON'}).encode('utf-8')
            self.send_response(400)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def log_message(self, *args):
        return  # avoid request logging containing sensitive material


def selftest():
    def good(lock, req):
        return {'intent_id': lock, 'answer': 'หลักฐานยังไม่เพียงพอสำหรับการยืนยัน',
                'claims': [], 'requested_action': None,
                'executed': False, 'outcome': 'NOT_EXECUTED'}
    def make(fn, req):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / 'audit.jsonl'
            gateway = Gateway(path, fn)
            result = gateway.process(req)
            integrity = gateway.audit.verify()
            return result, integrity, path.read_text(encoding='utf-8')
    cases = []
    base = {'intent': 'ยืนยันเท่าที่มีหลักฐาน', 'task': 'สรุปข้อเท็จจริง', 'evidence': []}
    r, ok, _ = make(good, base)
    cases.append(('no-claims cannot leak model reply', r['status'] == 'ABSTAIN_NO_VERIFIED_EVIDENCE' and 'หลักฐานที่ผ่าน' in r['answer'] and ok))
    r, ok, _ = make(good, {'task':'missing intent'})
    cases.append(('missing intent denied', r['status']=='BLOCKED' and r['reason']=='INTENT_REQUIRED' and ok))
    r, ok, _ = make(lambda lock,req:{**good(lock,req),'intent_id':'forged'}, base)
    cases.append(('intent mismatch blocked', r.get('reason')=='INTENT_LOCK_MISMATCH' and ok))
    r, ok, _ = make(lambda lock,req:{**good(lock,req),'requested_action':'delete files'}, base)
    cases.append(('unapproved tool use denied', r.get('reason')=='ACTION_BLOCKED_NO_EXECUTOR' and ok))
    r, ok, _ = make(lambda lock,req:{**good(lock,req),'executed':True}, base)
    cases.append(('false execution denied', r.get('reason')=='EXECUTION_CLAIM_NOT_PROVEN' and ok))
    r, ok, _ = make(lambda lock,req:{**good(lock,req),'claims':[{'text':'fact','evidence_ids':['fake']}]}, base)
    cases.append(('fabricated evidence denied', r.get('reason')=='CLAIM_WITHOUT_KNOWN_EVIDENCE' and ok))
    r, ok, _ = make(lambda lock,req:{**good(lock,req),'claims':[{'text':'observation','evidence_ids':['E1']}]},
                    {**base,'evidence':[{'id':'E1','text':'Claimed observation'}]})
    cases.append(('known evidence requires independent review', r['status']=='EVIDENCE_REVIEW_REQUIRED' and r['answer'] is None and not r['verified_truth'] and ok))
    r, ok, _ = make(good, {**base, 'risk':'medical'})
    cases.append(('medical requires human reviewer', r['status']=='HUMAN_REVIEW_REQUIRED' and r['answer'] is None and ok))
    r, ok, _ = make(good, {**base,'evidence':[{'id':'E1','text':'one'},{'id':'E1','text':'two'}]})
    cases.append(('duplicate evidence ids rejected', r.get('reason')=='DUPLICATE_EVIDENCE_ID' and ok))
    with tempfile.TemporaryDirectory() as d:
        path = pathlib.Path(d) / 'audit.jsonl'
        audit = HashAudit(path)
        audit.append({'stage':'TEST'})
        tamper_before = audit.verify()
        path.write_text(path.read_text(encoding='utf-8').replace('TEST','EDIT'),encoding='utf-8')
        tamper_after = audit.verify()
        cases.append(('hash chain detects editing', tamper_before and not tamper_after))
    with tempfile.TemporaryDirectory() as d:
        path = pathlib.Path(d) / 'audit.jsonl'
        path.write_text('',encoding='utf-8')
        audit = object.__new__(HashAudit)
        audit.path = path
        cases.append(('empty ledger not treated valid', not audit.verify()))
    with tempfile.TemporaryDirectory() as d:
        # Backend is not configured; should block without hallucinating response.
        original = dict(os.environ)
        try:
            os.environ.pop('OLGM_PROVIDER', None)
            os.environ.pop('OLGM_MODEL', None)
            r = Gateway(pathlib.Path(d)/'audit.jsonl').process(base)
        finally:
            os.environ.clear(); os.environ.update(original)
        cases.append(('unconfigured model fails closed',r.get('reason')=='MODEL_NOT_CONFIGURED'))
    passed = sum(bool(x) for _, x in cases)
    for name, result in cases:
        print(('PASS' if result else 'FAIL') + ' | ' + name)
    print(canon({'total':len(cases),'passed':passed,'failed':len(cases)-passed,
                 'model_calls_real':0,'scope':'simulated provider / gateway contract only'}))
    return passed == len(cases)


def main():
    p = argparse.ArgumentParser(description='OLGM observable gateway proof of concept')
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--self-test',action='store_true')
    group.add_argument('--demo',action='store_true')
    group.add_argument('--run',metavar='REQUEST_JSON')
    group.add_argument('--serve',action='store_true')
    p.add_argument('--audit',default='olgm_audit.jsonl')
    args = p.parse_args()
    if args.self_test:
        raise SystemExit(0 if selftest() else 1)
    if args.demo:
        # Demonstration is clearly labeled as a simulated provider.
        req = {'intent':'ตอบอย่างตรงไปตรงมา', 'task':'ยืนยันว่ามีผลการรันจริงหรือไม่', 'evidence':[]}
        fake = lambda lock,req:{'intent_id':lock,'answer':'ยังไม่มีผลการทดสอบโมเดลจริง',
                 'claims':[], 'requested_action':None,'executed':False,'outcome':'NOT_EXECUTED'}
        with tempfile.TemporaryDirectory() as d:
            print(canon(Gateway(pathlib.Path(d)/'audit.jsonl',fake).process(req)))
        return
    gateway = Gateway(args.audit)
    if args.run:
        req = json.loads(pathlib.Path(args.run).read_text(encoding='utf-8'))
        print(json.dumps(gateway.process(req),ensure_ascii=False,indent=2))
    else:
        API.gateway = gateway
        # Safe default: localhost only, no public LAN exposure, no authentication in this POC.
        server = ThreadingHTTPServer(('127.0.0.1', 8765), API)
        print('OLGM gateway listening ONLY on http://127.0.0.1:8765/run')
        server.serve_forever()


if __name__ == '__main__':
    main()
