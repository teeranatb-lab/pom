"""Explicit opt-in external research adapter with evidence quarantine.

No built-in web requests. An injected provider must return source observations.
Results are registered but never promoted to verified facts automatically.
"""
import hashlib
import uuid


class ResearchAdapter:
    def __init__(self,ms,canti,audit):
        self.ms=ms;self.canti=canti;self.audit=audit

    def search(self,query,provider=None,allow_external_query=False,limit=5,trace_id=None):
        if not allow_external_query:
            return {'status':'DENIED','reason':'external_query_requires_explicit_opt_in'}
        if not self.canti.check('read','research.external')['allowed']:
            return {'status':'DENIED','reason':'CANTI_external_read_grant_required'}
        if not callable(provider):
            return {'status':'NOT_TESTED','reason':'external_provider_not_connected'}
        if not isinstance(query,str) or not query.strip() or len(query)>2000:
            return {'status':'DENIED','reason':'invalid_query'}
        results=[]
        for item in list(provider(query,min(max(1,int(limit)),10)))[:limit]:
            if not isinstance(item,dict) or not item.get('source_url') or not item.get('content'):
                continue
            doc={'source_url':str(item['source_url'])[:1000],'title':str(item.get('title',''))[:200],
                 'content':str(item['content'])[:20000], 'license':item.get('license')}
            ref='retrieved_'+hashlib.sha256((doc['source_url']+'\n'+doc['content']).encode()).hexdigest()[:24]
            try:
                if not self.canti.check('sandbox_write','evidence')['allowed']:
                    return {'status':'BLOCKED','reason':'evidence_write_grant_required',
                            'unpersisted_results':len(results)}
                self.ms.add_evidence(ref,'retrieved_untrusted',doc['content'],
                                     source_url=doc['source_url'],license=doc['license'])
            except Exception as exc:
                if self.ms.get_evidence(ref) is None:
                    return {'status':'ERROR','reason':str(exc)[:200]}
            results.append({'evidence_ref':ref,'source_url':doc['source_url'],
                            'title':doc['title'],'source_status':'FETCHED_UNVERIFIED'})
        trace_id=trace_id or str(uuid.uuid4())
        self.audit.append(trace_id,'EXTERNAL_RESEARCH_CANDIDATE',
                          {'query_sha256':hashlib.sha256(query.encode()).hexdigest(),
                           'evidence_refs':[x['evidence_ref'] for x in results]})
        return {'status':'RETRIEVED_CANDIDATES','results':results,
                'verified_fact_count':0,'external_provider_attested':False}
