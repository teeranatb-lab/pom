"""Method-plan selection only; execution of listed methods is not implemented."""
METHODS = {1:'origin_intent',2:'observation',3:'comparison',4:'classification',
    5:'spatial',6:'analytical',7:'deduction',8:'induction',9:'abduction',
    10:'critical',11:'divergent',12:'lateral',13:'analogical',14:'synthesis',
    15:'systems',16:'causal',17:'scenario',18:'metacognition',19:'decision'}
INTENT_TO_METHODS = {
    'impact':[2,15,16,19], 'why':[2,9,16,19], 'where':[2,5,19],
    'how':[2,6,14,19], 'true':[2,7,10,19], 'numeric':[2,7,19],
    'route':[2,5,17,19], 'career':[2,6,11,17,19],
    'clean':[2,6,12,19], 'observation':[2,6,19]}

def select_methods(intent_tag, budget='normal'):
    tags = INTENT_TO_METHODS.get(intent_tag,[2,6,19])
    if budget == 'tight':
        tags = [*tags[:2],19]
    return list(dict.fromkeys([1,*tags,19]))
