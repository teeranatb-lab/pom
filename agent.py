"""Restricted candidate-generating agent; no silent semantic mutations."""
import ast
import operator
import re
import uuid
from .observer import Observer
from .episodic import EpisodicMemory
from .methods import select_methods


_BINOPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,
        ast.Div:operator.truediv,ast.FloorDiv:operator.floordiv,ast.Mod:operator.mod}
_UNARYOPS={ast.UAdd:operator.pos,ast.USub:operator.neg}


def _arithmetic(expression):
    """Small, safe arithmetic expression evaluator: no names, calls or powers."""
    if len(expression)>80 or not re.fullmatch(r'[0-9.\s+*/%()\-]+',expression):
        raise ValueError('unsupported arithmetic input')
    def evaluate(node, depth=0):
        if depth>20:
            raise ValueError('too deep')
        if isinstance(node,ast.Expression):
            return evaluate(node.body,depth+1)
        if isinstance(node,ast.Constant) and type(node.value) in (float,int):
            if abs(node.value)>1e12: raise ValueError('number too large')
            return node.value
        if isinstance(node,ast.BinOp) and type(node.op) in _BINOPS:
            result=_BINOPS[type(node.op)](evaluate(node.left,depth+1),evaluate(node.right,depth+1))
            if abs(result)>1e15: raise ValueError('result too large')
            return result
        if isinstance(node,ast.UnaryOp) and type(node.op) in _UNARYOPS:
            return _UNARYOPS[type(node.op)](evaluate(node.operand,depth+1))
        raise ValueError('unsupported math syntax')
    return evaluate(ast.parse(expression,mode='eval'))


class Agent:
    def __init__(self, ms, model, audit, canti, otfa):
        self.ms,self.audit,self.canti,self.otfa=ms,audit,canti,otfa
        self.observer=Observer(ms,model,audit)
        self.episodic=EpisodicMemory(ms.db_path,ms)

    def ask(self, question, intent_tag='true', candidate_cids=None, allow_web=False):
        trace_id=str(uuid.uuid4())
        if not self.canti.check('reason','agent.ask')['allowed']:
            return {'status':'DENIED','reason':'CANTI_no_grant','trace_id':trace_id}
        if allow_web:
            return {'status':'NOT_IMPLEMENTED','reason':'web_tool_not_wired','trace_id':trace_id}
        methods=select_methods(intent_tag)
        if intent_tag=='numeric':
            try:
                result=_arithmetic(question)
            except Exception as exc:
                return {'status':'INSUFFICIENT','reason':str(exc),'trace_id':trace_id}
            answer=f'{result:g}' if isinstance(result,float) else str(result)
            self.audit.append(trace_id,'DETERMINISTIC_MATH',{'expression':question,'answer':answer})
            return {'status':'DETERMINISTIC_RESULT','trace_id':trace_id,
                    'answer':answer,'method':'safe_arithmetic','methods_planned':methods,
                    'proof_level':'computed_locally'}
        obs=self.observer.observe(trace_id,intent_tag,question,candidate_cids)
        if obs['status']!='CANDIDATE_OBSERVATION':
            return {'status':'INSUFFICIENT','trace_id':trace_id,'observation':obs}
        rel=obs['relation']
        claim={'text':question,'claim_type':'inferred','evidence_refs':
               [rel['evidence_ref']] if rel.get('evidence_ref') else [],'relation_id':None}
        verdict=self.otfa.verify(claim)
        cores=obs['meaning_cores']
        names=[c.get('cid') or c.get('proposed_surface') for c in cores]
        result={'status':'CANDIDATE','trace_id':trace_id,'intent':intent_tag,
                'methods_planned':methods,
                'answer_candidate':(obs.get('composite') or {}).get('definition'),
                'observation':obs,'otfa':verdict,
                'ai_recommendation':{'status':'CANDIDATE',
                    'text':f'Explore {rel["type"]} between '+', '.join(names[:2])},
                'unknowns':obs['provenance']['unknowns']}
        self.audit.append(trace_id,'ANSWER_CANDIDATE',
                          {'answer_candidate':result['answer_candidate'],'otfa':verdict['overall']})
        return result
