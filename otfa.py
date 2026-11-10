"""Conservative three-plane evidence gate.

A reference existing in SQLite is not proof that it supports a claim.
"""
class OTFA:
    def __init__(self, meaning_space):
        self.ms = meaning_space

    def verify(self, claim):
        planes = {'empirical':self._empirical(claim),
                  'theory':self._theory(claim),
                  'relation':self._relation(claim)}
        statuses = {v['status'] for v in planes.values()}
        if 'CONTRADICTED' in statuses:
            overall = 'CONTRADICTED'
        elif statuses == {'SUPPORTED'}:
            overall = 'SUPPORTED'
        elif 'INSUFFICIENT' in statuses:
            overall = 'INSUFFICIENT'
        else:
            overall = 'NOT_TESTED'
        return {'overall':overall,'planes':planes,
                'disclosure':'References and model outputs are not independently validated factual proofs.'}

    def _empirical(self, claim):
        refs = claim.get('evidence_refs') or []
        if not refs:
            return {'status':'INSUFFICIENT','reason':'no_evidence'}
        for ref in refs:
            if not self.ms.get_evidence(ref):
                return {'status':'INSUFFICIENT','reason':f'evidence_not_found:{ref}'}
        return {'status':'NOT_TESTED','reason':'evidence_registered_not_claim_verified'}

    def _theory(self, claim):
        return {'status':'NOT_TESTED','reason':'independent_theory_check_not_implemented'}

    def _relation(self, claim):
        rid = claim.get('relation_id')
        if not rid:
            return {'status':'NOT_TESTED','reason':'no_persisted_relation_to_check'}
        edge = self.ms.get_edge(rid)
        if not edge:
            return {'status':'INSUFFICIENT','reason':'edge_not_found'}
        # Even a marked 'verified' edge is not proof of a claim unless the edge
        # verification process is independently trusted and bound to this claim.
        return {'status':'NOT_TESTED','reason':f'edge_status:{edge["verification_status"]}'}
