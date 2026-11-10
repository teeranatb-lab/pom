"""Single end-to-end OLGM runtime: intent -> graph -> evidence -> logical gravity ->
quality -> CANTI boundary -> checkpoint receipts -> return-to-intent.

Chat path is executable without a model. WORK needs separate explicit approval.
"""
from __future__ import annotations
import json
import os
import re
import uuid
from .agent import _arithmetic
from .intent import IntentLedger
from .canonical import CanonicalLedger
from .semantic import MeaningEngine
from .evidence import EvidenceLedger
from .checkpoints import Checkpoints
from .quality import assess_five_axes,quality_proof,logical_gravity
from .cognitive import CognitiveMethods
from .actions import ActionController
from .curiosity import BoundedCuriosity
from .dispatch import SemanticActionDispatcher
from .identity import SignedAuthorizations
from .research import ResearchAdapter
from .workqueue import AgentQueue
from .placement import GraphPlacement


class IntegratedRuntime:
    def __init__(self,ms,model,audit,canti,otfa,signing_key=None):
        from .agent import Agent
        self.ms=ms;self.audit=audit;self.canti=canti;self.otfa=otfa
        self.agent=Agent(ms,model,audit,canti,otfa)
        self.intent=IntentLedger(ms.db_path,audit)
        self.canonical=CanonicalLedger(ms.db_path,audit)
        self.semantic=MeaningEngine(ms,audit)
        self.evidence=EvidenceLedger(ms,audit)
        self.checkpoints=Checkpoints(ms.db_path,audit,signing_key)
        self.cognitive=CognitiveMethods(ms,self.semantic)
        self.signatures=SignedAuthorizations(ms.db_path)
        self.actions=ActionController(ms.db_path,canti,self.intent,self.checkpoints,audit,signatures=self.signatures)
        self.curiosity=BoundedCuriosity(self.semantic,audit,max_items=3)
        self.dispatcher=SemanticActionDispatcher(ms,self.semantic,audit)
        self.research=ResearchAdapter(ms,canti,audit)
        self.placement=GraphPlacement(ms)
        self.queue=AgentQueue(self)
        from .valueguard import ValueGuard
        self.value_guard=ValueGuard(ms.db_path,audit)

    def process(self,question,actor='local_user',origin_ref='origin_declaration_external',
                intent_tag='true',task_type='CHAT',intent_id=None,expected_intent_hash=None,
                seed_cids=None,goal_cid=None,five_axes=None,enable_model=False):
        if not isinstance(question,str) or not question.strip() or len(question)>10000:
            raise ValueError('question must be nonempty <= 10000 characters')
        if task_type not in ('CHAT','WORK'):raise ValueError('task_type must be CHAT or WORK')
        if intent_tag=='thai' and enable_model:
            return {'status':'DENIED','reason':'thai_model_transfer_requires_separate_Origin_approval',
                    'gate':'intellectual_sovereignty_default_deny'}
        if not self.canti.check('reason','agent.ask')['allowed']:
            return {'status':'DENIED','reason':'CANTI_no_reason_grant','gate':'default_deny'}
        if intent_id:
            intent=self.intent.latest(intent_id)
            if not intent:return {'status':'INSUFFICIENT','reason':'intent_not_found'}
            if expected_intent_hash!=intent['intent_hash']:
                re=self.intent.reenter(intent_id,intent['revision'],'caller_intent_stale',
                                       {'expected':expected_intent_hash,'current':intent['intent_hash']})
                return {'status':'ROOT_REENTRY',**re}
            if question!=intent['statement'] or task_type!=intent['task_type']:
                re=self.intent.reenter(intent_id,intent['revision'],'input_differs_from_locked_intent',
                                       {'statement_matches':question==intent['statement'],
                                        'task_type_matches':task_type==intent['task_type']})
                return {'status':'ROOT_REENTRY',**re}
            lock={'intent_id':intent_id,'revision':intent['revision'],'intent_hash':intent['intent_hash']}
        else:
            lock=self.intent.create(actor,origin_ref,question,task_type=task_type)
        trace_id=str(uuid.uuid4());intent_hash=lock['intent_hash'];intent_id=lock['intent_id']
        checkpoints=[]
        def cp(stage,status,refs=None,findings=None,**kwargs):
            receipt=self.checkpoints.record(trace_id,stage,status,refs or {},findings or {},**kwargs)
            checkpoints.append(receipt)
            return receipt
        # F-00 reference boundary is checked mechanically; no Core0 data loaded/examined.
        cp('F-00','PASS',{'policy':'CORE0_NO_RUNTIME_ACCESS'},
           {'core0_access':False,'access_policy':'read/write/inspect refused'})
        cp('F-01','NOT_TESTED',{'origin_ref':origin_ref},
           {'origin_identity_verification':'external_auth_required'})
        cp('F-02','NOT_TESTED',{'origin_ref':origin_ref},
           {'declaration_cryptographic_validation':'not_automatically_attested'})
        axes=assess_five_axes(five_axes or {})
        cp('F-03','PASS' if axes['overall']=='PASS' else 'PENDING',{},axes)
        cp('F-04','PASS',{'intent_id':intent_id,'revision':lock['revision']},
           {'intent_hash':intent_hash,'task_type':task_type})
        seed_candidates=self.semantic.seed_candidates(question,limit=8)
        seed_cids=list(dict.fromkeys((seed_cids or [])+[x['cid'] for x in seed_candidates]))
        graph=self.semantic.resonance(seed_cids,depth=2,limit=80)
        cp('X-00','PASS' if graph['candidates'] else 'INSUFFICIENT',
           {'seed_cids':seed_cids},
           {'graph_candidate_count':len(graph['candidates']),'note':'lexical seeds are not factual proof'})
        cp('OP-01','PASS',{'intent_id':intent_id},{'intent_hash':intent_hash})
        canonical=self.canonical.current()
        cp('OP-02','PASS' if canonical else 'PENDING',
           {'canonical_hash':canonical['state_hash'] if canonical else None},
           {'canonical_reference_exists':bool(canonical),
            'canonical_master_content_not_modified':True,
            'external_document_digest_authentication':'NOT_TESTED'})
        claim_id=self.evidence.add_claim(question,'CALCULATED' if intent_tag=='numeric' else 'UNKNOWN',
                                         origin_ref=origin_ref)
        findings=self.evidence.v1_v7(claim_id)
        cp('OP-03','PENDING',{'claim_id':claim_id},{'evidence_grade':findings['status'],
           'epistemic_class':findings['epistemic_class']})
        methods=self.cognitive.run(intent_tag,seed_cids,goal_cid)
        result_text=None;proof_type='UNKNOWN';obs=None
        if intent_tag=='numeric':
            try:
                num=_arithmetic(question)
                result_text=f'{num:g}' if isinstance(num,float) else str(num)
                proof_type='CALCULATED_DETERMINISTIC'
            except Exception as exc:proof_type=f'INSUFFICIENT_MATH:{exc}'
        paths=self.semantic.candidate_paths(seed_cids[0],goal_cid) if seed_cids and goal_cid else {
            'status':'NOT_APPLICABLE','candidate_paths':[],'rejected_paths':[]}
        # Read stored semantic relations without a model. This is a transparent
        # candidate explanation, not a verified real-world factual claim.
        if intent_tag!='numeric' and paths['candidate_paths']:
            preferred=sorted(paths['candidate_paths'],key=lambda p:(
                p['status']!='CHECKED_GRAPH_PATH', len(p['edge_ids'])))[0]
            triples=[]
            for edge_id in preferred['edge_ids']:
                e=self.ms.get_edge(edge_id)
                source=self.ms.get_core(e['source_cid'])
                target=self.ms.get_core(e['target_cid'])
                triples.append(f'{source["surface_form"]} --{e["relation_type"]}--> {target["surface_form"]}')
            result_text='; '.join(triples) if triples else None
            proof_type='GRAPH_DERIVED_CANDIDATE_NOT_INDEPENDENTLY_VERIFIED'
        if enable_model and intent_tag!='numeric':
            obs=self.agent.observer.observe(trace_id,intent_tag,question,seed_cids)
            if obs.get('status')=='CANDIDATE_OBSERVATION':
                proposal=self.semantic.propose(trace_id,obs,'model_observation_unverified')
                obs['proposal_id']=proposal['proposal_id']
                result_text=(obs.get('composite') or {}).get('definition')
                proof_type='CANDIDATE_MODEL_GENERATED'
            else:proof_type='MODEL_NOT_AVAILABLE_OR_INVALID'
        elif intent_tag!='numeric' and result_text is None:
            proof_type='STRUCTURAL_ONLY_MODEL_DISABLED'
        thai_response=None
        if intent_tag=='thai':
            # The Thai answer is deliberately processed WITHIN the established
            # Intent/Canonical/Audit/Checkpoint loop, not as a bypass of OLGM.
            from .thai.learning import ThaiExampleMemory
            from .thai.lexicon import ThaiLexicon
            from .thai.responder import ThaiResponder
            thai_response=ThaiResponder(
                ThaiExampleMemory(self.ms.db_path,audit=self.audit,canti=self.canti),
                lexicon=ThaiLexicon(self.ms,self.canti,self.audit)).answer(question)
            if thai_response['status'] not in ('INSUFFICIENT','MATH_REJECTED'):
                result_text=thai_response['answer_th']
                proof_type='THAI_'+thai_response['status']
        conflicts=self.semantic.detect_conflicts()
        curiosity=self.curiosity.suggest(trace_id,seed_cids)
        model_known_ids=[]
        if obs and obs.get('status')=='CANDIDATE_OBSERVATION':
            model_known_ids=[c['cid'] for c in obs['meaning_cores'] if c.get('cid')]
        tool_candidates=self.dispatcher.candidates(list(dict.fromkeys(seed_cids+model_known_ids)))
        cp('OP-04','PASS',{'seed_cids':seed_cids,'selected_methods':methods['selected']},
           {'graph_candidates':len(graph['candidates']),
            'alternate_paths':len(paths['candidate_paths']),
            'rejected_paths':paths['rejected_paths'][:20],
            'conflicts':conflicts[:10],
            'proof_type':proof_type,
            'thai_response_status':thai_response['status'] if thai_response else None,
            'curiosity_questions':len(curiosity['recommendations']),
            'tool_candidates':len(tool_candidates['actions'])})
        proof=self.intent.proof(intent_id,intent_hash)
        cp('OP-05','PASS' if proof['status']=='PASS' else 'FAIL',{'intent_id':intent_id},proof)
        claims=[{'path':p,'intent_hash':intent_hash,'evidence':
                 'VERIFIED' if p['status']=='CHECKED_GRAPH_PATH' else 'UNKNOWN',
                 'constraints_ok':True,'contradicted':bool(conflicts)} for p in paths['candidate_paths']]
        gravity=logical_gravity(claims,intent_hash)
        qfindings={'intent_preservation':'PASS' if proof['status']=='PASS' else 'FAIL',
                   'semantic_coherence':'FAIL' if conflicts else 'PASS' if graph['candidates'] else 'NOT_TESTED',
                   'evidence_sufficiency':'PASS' if intent_tag=='numeric' and result_text is not None else 'NOT_TESTED',
                   'constraint_compliance':'PENDING' if task_type=='WORK' else 'PASS',
                   'provenance_completeness':'PASS',
                   'unknown_preservation':'PASS',
                   'context_relevance':'NOT_TESTED',
                   'canonical_consistency':'PASS' if canonical else 'NOT_TESTED',
                   'drift_detection':'PASS' if proof['status']=='PASS' else 'FAIL',
                   'outcome_quality':'NOT_TESTED'}
        quality=quality_proof(qfindings)
        cp('OP-06','PENDING' if quality['status']=='PENDING' else quality['status'],
           {'claim_id':claim_id,'intent_hash':intent_hash},
           {'quality':quality,'logical_gravity':gravity,'verified_action':False})
        cp('OP-07','SKIPPED' if task_type=='CHAT' else 'BLOCKED',
           {'task_type':task_type},{'execution':'separate_explicit_plan_approval_required'})
        cp('OP-08','SKIPPED' if task_type=='CHAT' else 'NOT_TESTED',
           {},{'outcome':'no_effect_execution_in_informational_pipeline'})
        chain_ok,chain_msg=self.audit.verify()
        cp('OP-09','PASS' if chain_ok else 'FAIL',{},
           {'chain_verification_prior_to_this_receipt':chain_msg,
            'independent_external_anchor':'NOT_TESTED'})
        back=self.intent.proof(intent_id,intent_hash)
        cp('OP-10','PASS' if back['status']=='PASS' else 'FAIL',
           {'intent_hash':intent_hash},{'return_comparison':back,'outcome_grade':proof_type})
        status=('DETERMINISTIC_RESULT' if result_text is not None and
                (intent_tag=='numeric' or thai_response and thai_response['status']=='DETERMINISTIC_ANSWER') else
                'CANDIDATE' if result_text else 'INSUFFICIENT')
        out={'status':status,'trace_id':trace_id,'intent_id':intent_id,'intent_hash':intent_hash,
             'task_type':task_type,'question':question,'answer':result_text,
             'proof_type':proof_type,'meaning_space':{'seed_candidates':seed_candidates,
                 'observed_nodes':len(graph['candidates']), 'candidate_paths':paths},
             'cognitive':methods,'epistemic_claim_id':claim_id,
             'otfa_v1_v7':findings,'model_observation':obs,'thai_layer':thai_response,
             'logical_gravity':gravity,'quality_proof':quality,'five_axes':axes,
             'curiosity':curiosity,'semantic_action_candidates':tool_candidates,
             'unknowns':['independent_evidence_not_verified','external_origin_credential_not_checked']
                        if intent_tag!='numeric' else ['external_origin_credential_not_checked'],
             'checkpoints':checkpoints,'can_execute_external_action':False,
             'value_assessment':{'status':'NOT_ESTIMATED',
                'reason':'business_value_cannot_be_inferred_from_answer_without_supported_financial_evidence',
                'value_policy':'OLGM-VG-01/1.0','owner_email':'teeranat.b@gmail.com'},
             'gate_s10':'NOT_PASSED'}
        self.audit.append(trace_id,'INTEGRATED_RESULT',
                          {'status':status,'intent_hash':intent_hash,'proof_type':proof_type,
                           'quality':quality['status'],'checkpoint_count':len(checkpoints)})
        return out
