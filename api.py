"""Small loopback-only development API. DO NOT expose to LAN/Internet unprotected."""
import json
import hmac
from .production import is_production
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def serve(agent, host='127.0.0.1',port=8765,integrated=None,admin_token=None):
    if host not in ('127.0.0.1','localhost','::1'):
        raise ValueError('Only loopback bind permitted; add real authentication before LAN access')
    if is_production() and (not admin_token or len(admin_token)<32 or len(set(admin_token))<12):
        raise PermissionError('production requires a strong OLGM_HTTP_TOKEN and externally managed TLS/identity; API listener remains loopback')
    class Handler(BaseHTTPRequestHandler):
        def _send(self,status,doc):
            payload=json.dumps(doc,ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path=='/health':
                self._send(200,{'status':'OK',
                    'model':'redacted' if is_production() else agent.observer.model.name,
                    'security':'loopback_only_not_independently_certified'})
            else:
                self._send(404,{'status':'NOT_FOUND'})

        def do_POST(self):
            allowed={'/api/ask','/api/observe','/api/experience','/api/process','/api/thai/answer'}
            if self.path not in allowed:
                return self._send(404,{'status':'NOT_FOUND'})
            try:
                if (is_production() or admin_token) and not hmac.compare_digest(
                      self.headers.get('X-OLGM-Token',''),admin_token):
                    return self._send(401,{'status':'DENIED','reason':'invalid_token'})
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=65536:
                    return self._send(413,{'status':'REJECTED','reason':'invalid_body_size'})
                body=json.loads(self.rfile.read(length))
                if not isinstance(body,dict):
                    raise ValueError('object required')
                if is_production() and self.path in ('/api/observe','/api/experience'):
                    return self._send(403,{'status':'DENIED','reason':'production_writes_require_separate_approved_identity_gateway'})
                if is_production() and body.get('enable_model'):
                    return self._send(403,{'status':'DENIED','reason':'external_or_local_model_requires_separate_origin_release_and_egress_policy'})
                if self.path=='/api/thai/answer':
                    # Thai retrieval may contain locally restricted examples. No unauthenticated API access.
                    if not admin_token:
                        return self._send(403,{'status':'DENIED','reason':'thai_api_token_required'})
                    if integrated is None:
                        return self._send(501,{'status':'NOT_IMPLEMENTED'})
                    from .thai.learning import ThaiExampleMemory
                    from .thai.responder import ThaiResponder
                    from .thai.lexicon import ThaiLexicon
                    result=ThaiResponder(ThaiExampleMemory(integrated.ms.db_path),
                         lexicon=ThaiLexicon(integrated.ms,integrated.canti,integrated.audit)).answer(body.get('q',''))
                elif self.path=='/api/process':
                    if integrated is None:
                        return self._send(501,{'status':'NOT_IMPLEMENTED'})
                    result=integrated.process(body.get('q',''),intent_tag=body.get('intent','true'),
                        task_type=body.get('task_type','CHAT'), enable_model=bool(body.get('enable_model',False)))
                elif self.path=='/api/ask':
                    result=agent.ask(body.get('q',''),body.get('intent','true'))
                elif self.path=='/api/observe':
                    if not agent.canti.check('reason','agent.ask')['allowed']:
                        return self._send(403,{'status':'DENIED'})
                    import uuid
                    result=agent.observer.observe(str(uuid.uuid4()),body.get('intent','observation'),body.get('text',''))
                else:
                    if not agent.canti.check('sandbox_write','episode.record')['allowed']:
                        return self._send(403,{'status':'DENIED'})
                    result=agent.episodic.record(body.get('trace_id',''),body.get('intent',''),
                         body.get('start_cid',''),body.get('goal_cid',''),
                         body.get('relation_ids',[]),body.get('outcome','unresolved'),
                         body.get('evidence_ref'))
                status = 403 if result.get('status')=='DENIED' else 200
                self._send(status,result)
            except (ValueError,TypeError,KeyError) as exc:
                self._send(400,{'status':'BAD_REQUEST','reason':str(exc)})
    server=ThreadingHTTPServer((host,port),Handler)
    print(f'OLGM local API at http://{host}:{port} (not LAN-exposed)')
    try:
        server.serve_forever()
    finally:
        server.server_close()
