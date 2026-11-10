"""Pluggable, live AI observation with schema validation; untrusted output is a candidate."""
import json
from datetime import datetime, timezone


class ModelBackend:
    # Never expose live Meaning Space to unspecified/remote model providers.
    allow_internal_context = False
    def complete(self, system, user):
        raise NotImplementedError
    @property
    def name(self):
        return 'abstract'


class DisabledBackend(ModelBackend):
    def complete(self, system, user):
        raise RuntimeError('model_not_configured')
    @property
    def name(self):
        return 'disabled'


class OllamaBackend(ModelBackend):
    def __init__(self, host='http://127.0.0.1:11434', model='llama3.1'):
        self.host,self.model=host.rstrip('/'),model
        from urllib.parse import urlparse
        parsed=urlparse(self.host)
        self.allow_internal_context=(parsed.hostname in ('127.0.0.1','localhost','::1'))
    def complete(self, system, user):
        import requests
        response=requests.post(f'{self.host}/api/chat',json={
            'model':self.model,'messages':[{'role':'system','content':system},
               {'role':'user','content':user}], 'stream':False,'format':'json',
            'options':{'temperature':0.2}},timeout=180)
        response.raise_for_status()
        return response.json()['message']['content']
    @property
    def name(self):
        return f'ollama/{self.model}'


class OpenAICompatBackend(ModelBackend):
    def __init__(self, base_url, api_key, model):
        if not all([base_url,api_key,model]):
            raise ValueError('base_url, api_key, model required')
        self.base_url,self.api_key,self.model=base_url.rstrip('/'),api_key,model
    def complete(self, system, user):
        import requests
        response=requests.post(f'{self.base_url}/v1/chat/completions',
            headers={'Authorization':f'Bearer {self.api_key}'},
            json={'model':self.model,'messages':[{'role':'system','content':system},
                  {'role':'user','content':user}],
                  'temperature':0.2,'response_format':{'type':'json_object'}},
            timeout=180)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    @property
    def name(self):
        return f'openai-compat/{self.model}'


class Observer:
    SYSTEM = (
        'You are an OLGM observation candidate generator. Return strict JSON only. '
        'Return at least TWO meaning_cores. Each core has either cid (existing) '
        'or proposed_surface and language,definition,role. Return relation with '
        'type, source, target, direction, context, confidence (number 0..1), '
        'evidence_ref (null if unknown). source and target must match the cid or '
        'proposed_surface of distinct cores. Return composite:{definition}, '
        'provenance:{rationale,unknowns:[]}. Never fabricate evidence refs.'
    )

    def __init__(self, meaning_space, model, audit):
        self.ms,self.model,self.audit=meaning_space,model,audit

    def observe(self, trace_id, intent, observation_text, candidate_cids=None):
        ctx=(self.ms.context_snapshot(candidate_cids or [],limit=30)
             if self.model.allow_internal_context else [])
        user=f'INTENT: {intent}\nOBSERVATION: {observation_text}\nAVAILABLE_CIDS: {json.dumps(ctx,ensure_ascii=False)}'
        try:
            raw=self.model.complete(self.SYSTEM,user)
        except Exception as exc:
            return self._fail(trace_id,'model_unavailable',str(exc)[:200])
        try:
            data=json.loads(raw)
        except (ValueError, TypeError):
            return self._fail(trace_id,'model_output_not_json',str(raw)[:400])
        error=self._validate(data)
        if error:
            return self._fail(trace_id,error,data)
        result={'status':'CANDIDATE_OBSERVATION','actor':'AI_OBSERVER',
                'backend':self.model.name,'trace_id':trace_id,'intent':intent,
                'meaning_cores':data['meaning_cores'],'relation':data['relation'],
                'composite':data.get('composite') or {},
                'provenance':data.get('provenance') or {},
                'observed_at':datetime.now(timezone.utc).isoformat()}
        self.audit.append(trace_id,'OBSERVE_CANDIDATE',result)
        return result

    def _validate(self, data):
        if not isinstance(data,dict):
            return 'output_not_object'
        cores=data.get('meaning_cores')
        if not isinstance(cores,list) or len(cores)<2:
            return 'need_two_cores'
        identifiers=[]
        for core in cores:
            if not isinstance(core,dict):
                return 'invalid_core'
            ident=core.get('cid') or core.get('proposed_surface')
            if not isinstance(ident,str) or not ident.strip():
                return 'core_without_identity'
            if core.get('cid') and not self.ms.get_core(core['cid']):
                return 'unrecognized_cid'
            if not core.get('cid') and not (core.get('language') and core.get('definition')):
                return 'proposed_core_missing_metadata'
            identifiers.append(ident)
        rel=data.get('relation')
        if not isinstance(rel,dict) or not isinstance(rel.get('type'),str) or not rel['type'].strip():
            return 'relation_type_missing'
        if rel.get('source') not in identifiers or rel.get('target') not in identifiers:
            return 'relation_endpoints_unresolved'
        if rel.get('source') == rel.get('target'):
            return 'relation_endpoints_not_distinct'
        if rel.get('direction') not in ('forward','reverse','bidirectional'):
            return 'invalid_direction'
        confidence=rel.get('confidence')
        if isinstance(confidence,bool) or not isinstance(confidence,(float,int)) or not 0<=confidence<=1:
            return 'invalid_confidence'
        ev=rel.get('evidence_ref')
        if ev is not None and not self.ms.get_evidence(ev):
            return 'unknown_evidence_ref'
        provenance=data.get('provenance')
        if not isinstance(provenance,dict) or not isinstance(provenance.get('unknowns'),list):
            return 'unknowns_required'
        return None

    def _fail(self, trace_id, reason, raw):
        result={'status':'INSUFFICIENT','reason':reason,'trace_id':trace_id,
                'raw':str(raw)[:1000]}
        self.audit.append(trace_id,'OBSERVE_FAIL',result)
        return result
