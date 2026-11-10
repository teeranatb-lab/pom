"""Explicit multi-dimensional quality gates; never average away a hard failure."""
AXES=('ethics','morality','justice','compassion','truthfulness')
QUALITY=('intent_preservation','semantic_coherence','evidence_sufficiency',
         'constraint_compliance','provenance_completeness','unknown_preservation',
         'context_relevance','canonical_consistency','drift_detection','outcome_quality')
STATE={'PASS','FAIL','PENDING','NOT_TESTED'}


def assess_five_axes(inputs):
    if not isinstance(inputs,dict):raise ValueError('five_axes inputs must be dict')
    statuses={a:inputs.get(a,'NOT_TESTED') for a in AXES}
    if any(v not in STATE for v in statuses.values()):raise ValueError('invalid ethical status')
    return {'axes':statuses,'overall':'FAIL' if 'FAIL' in statuses.values() else
             'PASS' if all(v=='PASS' for v in statuses.values()) else 'PENDING',
             'disclosure':'A recorded self-assessment does not prove ethical compliance'}


def quality_proof(findings):
    """Missing tests => pending; hard FAIL is never concealed by successful checks."""
    results={name:findings.get(name,'NOT_TESTED') for name in QUALITY}
    if any(v not in STATE for v in results.values()):raise ValueError('invalid quality state')
    overall='FAIL' if 'FAIL' in results.values() else 'PASS' if all(v=='PASS' for v in results.values()) else 'PENDING'
    return {'status':overall,'criteria':results,'missing':[k for k,v in results.items() if v!='PASS']}


def logical_gravity(candidates, latest_intent_hash, evidence_grade='UNKNOWN'):
    """Retain all candidates, reject invalid constraints and order only by explicit grades.
    No invented probabilities; NOT_TESTED candidates remain visible and non-actionable.
    """
    result=[]
    for i,c in enumerate(candidates):
        reasons=[]
        if c.get('intent_hash') !=latest_intent_hash:reasons.append('intent_drift')
        if c.get('contradicted'):reasons.append('contradicted')
        if c.get('constraints_ok') is False:reasons.append('constraint_violation')
        if c.get('evidence') not in ('SUPPORTED','VERIFIED','CHECKED'):
            reasons.append('insufficient_evidence')
        result.append({'index':i,'candidate':c,'status':'REJECTED' if any(
            x in reasons for x in ('intent_drift','contradicted','constraint_violation')) else
            'NON_ACTIONABLE' if reasons else 'ELIGIBLE_FOR_REVIEW',
            'reasons':reasons})
    return {'evaluated_paths':result,
            'selected_for_action':[r['index'] for r in result if r['status']=='ELIGIBLE_FOR_REVIEW'],
            'automatically_executed':False}
