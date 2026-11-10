"""OLGM Ultimate integrated local developer CLI. No Origin impersonation, no silent grants.

Use an isolated SQLite file. CLI grants are only for a trusted local dev machine;
they are NOT a substitute for production identity or Origin authorization.
"""
import argparse
import json
import os
import sys
import uuid
from olgm.meaning_space import MeaningSpace
from olgm.audit import AuditChain
from olgm.canti import CANTI
from olgm.otfa import OTFA
from olgm.observer import DisabledBackend,OllamaBackend,OpenAICompatBackend
from olgm.pipeline import IntegratedRuntime
from olgm.production import cli_allowed, is_production


def build_runtime():
    ms=MeaningSpace(os.getenv('OLGM_DB','olgm.db'))
    audit=AuditChain(ms.db_path,external_anchor_path=os.getenv('OLGM_ANCHOR'),
                     anchor_key=os.getenv('OLGM_ANCHOR_KEY'))
    canti=CANTI(ms.db_path)
    provider=os.getenv('OLGM_MODEL_PROVIDER','disabled')
    if provider=='ollama':
        model=OllamaBackend(os.getenv('OLLAMA_HOST','http://127.0.0.1:11434'),
                            os.getenv('OLGM_MODEL','deepseek-r1:7b'))
    elif provider=='openai':
        model=OpenAICompatBackend(os.getenv('OLGM_BASE_URL'),os.getenv('OLGM_API_KEY'),os.getenv('OLGM_MODEL'))
    else:model=DisabledBackend()
    return IntegratedRuntime(ms,model,audit,canti,OTFA(ms),
                             signing_key=os.getenv('OLGM_RECEIPT_SIGN_KEY'))


def need_grant(rt,resource):
    if not rt.canti.check('sandbox_write',resource)['allowed']:
        raise PermissionError(f'CANTI_no_grant for sandbox_write/{resource}; use local grant-dev')


def main(argv=None):
    p=argparse.ArgumentParser(description='OLGM Ultimate integrated local runtime')
    s=p.add_subparsers(dest='cmd',required=True)
    s.add_parser('init')
    s.add_parser('value-policy',help='OLGM sovereign high-value alert rule (no email sent)')
    a=s.add_parser('value-evaluate',help='stage origin-first notice from a JSON business estimate')
    a.add_argument('--input',required=True,help='Trusted caller supplied structured estimate JSON')
    a=s.add_parser('value-status');a.add_argument('case_id',nargs='?')
    a=s.add_parser('value-dispatch',help='send ONE queued email through TLS SMTP and local CANTI grant')
    a.add_argument('--send',action='store_true',help='explicit operator authorization to attempt a single email')
    a=s.add_parser('value-exempt',help='register signed Origin exemption for origin/family member')
    a.add_argument('--subject',required=True);a.add_argument('--role',choices=['origin','family'],required=True)
    a.add_argument('--evidence-ref',required=True);a.add_argument('--receipt-file',required=True)
    a.add_argument('--signature-file',required=True)
    a=s.add_parser('production-preflight',help='Local S10 production readiness checks; cannot self-authorize release')
    a.add_argument('--output');a.add_argument('--no-restore-drill',action='store_true')
    s.add_parser('thai-patterns',help='Overview of Thai language intent catalog')
    a=s.add_parser('thai-detect');a.add_argument('text')
    a=s.add_parser('thai-answer');a.add_argument('text')
    a=s.add_parser('thai-run',help='Thai answer with full OLGM Intent/Checkpoint/Audit governance');a.add_argument('text')
    a.add_argument('--actor',default='local_user');a.add_argument('--origin-ref',required=True)
    a=s.add_parser('thai-learn-propose');a.add_argument('question');a.add_argument('answer')
    a.add_argument('--origin-ref',required=True);a.add_argument('--source-ref',required=True)
    a.add_argument('--license',required=True);a.add_argument('--submitted-by',required=True)
    a.add_argument('--classification',choices=['PUBLIC','INTERNAL','PRIVATE','CONFIDENTIAL','ORIGIN_ONLY'],default='INTERNAL')
    s.add_parser('thai-learn-status')
    a=s.add_parser('thai-learn-receipt');a.add_argument('example_id');a.add_argument('--principal',required=True)
    a.add_argument('--expires-at',required=True)
    a=s.add_parser('thai-learn-approve');a.add_argument('example_id');a.add_argument('--receipt-file',required=True)
    a.add_argument('--signature-file',required=True)
    a=s.add_parser('thai-alias-propose');a.add_argument('alias');a.add_argument('cid')
    a.add_argument('--origin-ref',required=True);a.add_argument('--source-ref',required=True)
    a.add_argument('--license',required=True)
    a=s.add_parser('thai-alias-receipt');a.add_argument('alias_id');a.add_argument('--principal',required=True)
    a.add_argument('--expires-at',required=True)
    a=s.add_parser('thai-alias-approve');a.add_argument('alias_id');a.add_argument('--receipt-file',required=True)
    a.add_argument('--signature-file',required=True)
    a=s.add_parser('thai-alias-resolve');a.add_argument('word')
    s.add_parser('thai-code-list')
    a=s.add_parser('thai-code');a.add_argument('pattern');a.add_argument('--key');a.add_argument('--size',type=int,default=2)
    a.add_argument('--page',type=int,default=1);a.add_argument('--value');a.add_argument('--origin-ref',required=True)
    a.add_argument('--save',help='Optional *.py filename under generated; needs CANTI sandbox_write thai.generated')
    a=s.add_parser('thai-code-request');a.add_argument('request');a.add_argument('--origin-ref',required=True)
    a=s.add_parser('thai-synthesize');a.add_argument('examples_json')
    a.add_argument('--origin-ref',required=True);a.add_argument('--depth',type=int,default=4)
    a.add_argument('--save')
    a=s.add_parser('thai-code-pipeline');a.add_argument('steps',nargs='+')
    a.add_argument('--origin-ref',required=True)
    a.add_argument('--save',help='Optional *.py filename under generated; requires CANTI grant')
    a=s.add_parser('g06-propose',help='Stage and sandbox-test trusted code patch; never auto-apply')
    a.add_argument('intent')
    s.add_parser('g06-status')
    a=s.add_parser('g06-receipt');a.add_argument('proposal_id');a.add_argument('--principal',required=True)
    a.add_argument('--action',choices=['apply','rollback'],default='apply')
    a=s.add_parser('g06-apply');a.add_argument('proposal_id');a.add_argument('--receipt-file',required=True)
    a.add_argument('--signature-file',required=True)
    a=s.add_parser('g06-rollback');a.add_argument('proposal_id');a.add_argument('--receipt-file',required=True)
    a.add_argument('--signature-file',required=True)
    a=s.add_parser('selflearn-v2-cycle',help='G-06 bounded symbolic learning experimental')
    a.add_argument('--gens',type=int,default=12);a.add_argument('--batch',type=int,default=10)
    a.add_argument('--pop',type=int,default=48);a.add_argument('--intent')
    a.add_argument('--state',default='selflearn_v2_state.json')
    a=s.add_parser('selflearn-v2-report');a.add_argument('--state',default='selflearn_v2_state.json')
    a=s.add_parser('s10-evaluate',help='S-10 fail-closed release conformance report')
    a.add_argument('--trace-id');a.add_argument('--test-capture');a.add_argument('--manifest')
    a.add_argument('--evidence-root');a.add_argument('--trusted-keys-json')
    a.add_argument('--output')
    a=s.add_parser('s10-capture',help='capture real pytest results with source hashes')
    a.add_argument('--output',required=True);a.add_argument('--timeout',type=int,default=180)
    s.add_parser('audit-verify');s.add_parser('checkpoint-verify');s.add_parser('canonical-verify')
    a=s.add_parser('audit-anchor');a.add_argument('ref')
    a=s.add_parser('grant-dev');a.add_argument('scope');a.add_argument('resource');a.add_argument('--ttl',type=int,default=3600)
    a=s.add_parser('revoke');a.add_argument('grant_id')
    a=s.add_parser('run');a.add_argument('question');a.add_argument('--intent',default='true')
    a.add_argument('--task-type',choices=['CHAT','WORK'],default='CHAT');a.add_argument('--actor',default='local_user')
    a.add_argument('--origin-ref',default='external_declaration_ref');a.add_argument('--enable-model',action='store_true')
    a.add_argument('--seed',action='append',default=[]);a.add_argument('--goal')
    a=s.add_parser('ask');a.add_argument('question');a.add_argument('--intent',default='true')
    a=s.add_parser('observe');a.add_argument('text');a.add_argument('--intent',default='observation')
    a=s.add_parser('intent-lock');a.add_argument('text');a.add_argument('--actor',default='local_user')
    a.add_argument('--origin-ref',default='external_declaration_ref');a.add_argument('--task-type',choices=['CHAT','WORK'],default='CHAT')
    a=s.add_parser('intent-revise');a.add_argument('intent_id');a.add_argument('expected_hash');a.add_argument('--text');a.add_argument('--reason',required=True);a.add_argument('--actor',required=True)
    a=s.add_parser('intent-proof');a.add_argument('intent_id');a.add_argument('expected_hash')
    a=s.add_parser('canonical-init');a.add_argument('master_ref');a.add_argument('master_sha256');a.add_argument('--actor',required=True)
    a=s.add_parser('policy-ref');a.add_argument('policy_id');a.add_argument('declaration_ref');a.add_argument('sha256');a.add_argument('five_axes_ref');a.add_argument('version')
    a=s.add_parser('core-add');a.add_argument('cid');a.add_argument('language');a.add_argument('surface');a.add_argument('--definition');a.add_argument('--origin-ref',required=True)
    a=s.add_parser('edge-add');a.add_argument('edge_id');a.add_argument('source');a.add_argument('target');a.add_argument('type');a.add_argument('--origin-ref',required=True);a.add_argument('--context')
    a=s.add_parser('graph-search');a.add_argument('text')
    a=s.add_parser('graph-path');a.add_argument('source');a.add_argument('target')
    a=s.add_parser('evidence-add');a.add_argument('ref');a.add_argument('type');a.add_argument('content');a.add_argument('--source-url')
    a=s.add_parser('claim-add');a.add_argument('text');a.add_argument('--origin-ref',required=True);a.add_argument('--class-name',default='UNKNOWN')
    a=s.add_parser('claim-link');a.add_argument('claim_id');a.add_argument('evidence_ref');a.add_argument('type',choices=['supports','contradicts','mentions']);a.add_argument('excerpt');a.add_argument('--assessor',required=True);a.add_argument('--method',required=True)
    a=s.add_parser('claim-check');a.add_argument('claim_id')
    a=s.add_parser('edge-attest');a.add_argument('edge_id');a.add_argument('evidence_ref');a.add_argument('--authority',required=True);a.add_argument('--reason',required=True)
    a=s.add_parser('plan');a.add_argument('intent_id');a.add_argument('intent_hash');a.add_argument('action',choices=['sandbox.note','sandbox.counter']);a.add_argument('args_json');a.add_argument('--requested-by',required=True);a.add_argument('--idempotency-key',required=True)
    a=s.add_parser('approve');a.add_argument('plan_id');a.add_argument('--by',required=True);a.add_argument('--approval-ref',required=True)
    a.add_argument('--receipt-file');a.add_argument('--signature-file')
    a=s.add_parser('key-enroll-dev');a.add_argument('principal');a.add_argument('public_key_hex');a.add_argument('--authority',choices=['Origin','approver','reviewer'],required=True);a.add_argument('--enrolled-by',required=True)
    a=s.add_parser('execute');a.add_argument('plan_id')
    a=s.add_parser('gis-point');a.add_argument('lat',type=float);a.add_argument('lon',type=float)
    a=s.add_parser('gis-csv');a.add_argument('source_file');a.add_argument('destination_file')
    a=s.add_parser('media-ingest');a.add_argument('file');a.add_argument('--origin-ref',required=True)
    a=s.add_parser('queue-intent');a.add_argument('intent_id');a.add_argument('intent_hash');a.add_argument('--intent',default='why')
    a=s.add_parser('worker-step');a.add_argument('--limit',type=int,default=10)
    a=s.add_parser('core0-attempt');a.add_argument('operation')
    a=s.add_parser('serve');a.add_argument('--host',default='127.0.0.1');a.add_argument('--port',type=int,default=8765)
    # Sovereign Control Plane: registry, user-approved operations, and manual queue worker.
    s.add_parser('control-skills',help='List deterministic built-in skills')
    a=s.add_parser('control-install-skill');a.add_argument('skill_id');a.add_argument('--origin-ref',required=True)
    a=s.add_parser('control-register',help='Register a declared capability; never grants access')
    a.add_argument('resource_id');a.add_argument('kind',choices=['computer','plugin','space','skill'])
    a.add_argument('display_name');a.add_argument('--provider',required=True)
    a.add_argument('--actions',required=True,help='comma-separated exact actions')
    a.add_argument('--targets',default='',help='comma-separated exact permitted tool names or page IDs')
    a.add_argument('--classification',default='INTERNAL')
    a.add_argument('--ownership-ref',required=True);a.add_argument('--source-ref',required=True)
    a.add_argument('--connection-state',choices=['NOT_CONNECTED','DECLARED','CONNECTED','OFFLINE'],default='NOT_CONNECTED')
    a=s.add_parser('control-resources');a.add_argument('--kind',choices=['computer','plugin','space','skill'])
    a=s.add_parser('control-propose');a.add_argument('intent_id');a.add_argument('intent_hash')
    a.add_argument('resource_id');a.add_argument('action');a.add_argument('args_json')
    a.add_argument('--requested-by',required=True);a.add_argument('--idempotency-key',required=True)
    a=s.add_parser('control-receipt');a.add_argument('plan_id');a.add_argument('--principal',required=True)
    a.add_argument('--expires-at',required=True);a.add_argument('--approval-ref',required=True)
    a=s.add_parser('control-approve');a.add_argument('plan_id');a.add_argument('--receipt-file',required=True)
    a.add_argument('--signature-file',required=True)
    a=s.add_parser('control-enqueue');a.add_argument('plan_id');a.add_argument('--not-before')
    a.add_argument('--priority',type=int,default=0)
    a=s.add_parser('control-worker-step');a.add_argument('--limit',type=int,default=1)
    a=s.add_parser('control-cancel');a.add_argument('plan_id')
    a=s.add_parser('control-status');a.add_argument('--limit',type=int,default=50)
    args=p.parse_args(argv)
    # Refuse unsafe dev privilege bootstrap, mutation and execution in production mode.
    # The refusal happens before building the runtime and before any side effect.
    if not cli_allowed(args.cmd):
        print(json.dumps({'status':'DENIED','reason':'production_mode_blocks_dev_or_mutating_command',
                          'command':args.cmd,'gate_s10':'NOT_PASSED'},ensure_ascii=False,indent=2))
        return 3
    rt=build_runtime()
    try:
        if args.cmd.startswith('thai-'):
            from pathlib import Path
            from olgm.thai import ThaiIntentRouter
            from olgm.thai.patterns import stats as thai_stats
            from olgm.thai.learning import ThaiExampleMemory
            from olgm.thai.responder import ThaiResponder
            from olgm.thai.codegen import SafeCodeGenerator,capabilities as thai_code_capabilities
            mem=ThaiExampleMemory(rt.ms.db_path,audit=rt.audit,canti=rt.canti)
            if args.cmd=='thai-patterns':output=thai_stats()
            elif args.cmd=='thai-detect':output=ThaiIntentRouter().detect(args.text)
            elif args.cmd=='thai-run':
                output=rt.process(args.text,actor=args.actor,origin_ref=args.origin_ref,intent_tag='thai')
            elif args.cmd=='thai-answer':
                from olgm.thai.lexicon import ThaiLexicon
                output=ThaiResponder(mem,lexicon=ThaiLexicon(rt.ms,rt.canti,rt.audit)).answer(args.text)
            elif args.cmd=='thai-learn-propose':
                output=mem.propose(args.question,args.answer,args.origin_ref,args.source_ref,args.license,
                          args.submitted_by,args.classification)
            elif args.cmd=='thai-learn-status':output=mem.status()
            elif args.cmd=='thai-learn-receipt':
                output=mem.approval_receipt(args.example_id,args.principal,args.expires_at)
            elif args.cmd=='thai-learn-approve':
                receipt=json.load(open(args.receipt_file,encoding='utf-8'))
                signature=open(args.signature_file,encoding='utf-8').read().strip()
                output=mem.approve(args.example_id,receipt,signature)
            elif args.cmd.startswith('thai-alias-'):
                from olgm.thai.lexicon import ThaiLexicon
                lex=ThaiLexicon(rt.ms,rt.canti,rt.audit)
                if args.cmd=='thai-alias-propose':output=lex.propose(args.alias,args.cid,
                             args.origin_ref,args.source_ref,args.license)
                elif args.cmd=='thai-alias-receipt':output=lex.approval_receipt(args.alias_id,args.principal,args.expires_at)
                elif args.cmd=='thai-alias-approve':
                    receipt=json.load(open(args.receipt_file,encoding='utf-8'))
                    signature=open(args.signature_file,encoding='utf-8').read().strip()
                    output=lex.approve(args.alias_id,receipt,signature)
                else:output=lex.resolve(args.word)
            elif args.cmd=='thai-code-list':output=thai_code_capabilities()
            elif args.cmd=='thai-code':
                cg=SafeCodeGenerator(output_root=Path(__file__).resolve().parent/'generated',canti=rt.canti)
                output=cg.render(args.pattern,key=args.key,size=args.size,page=args.page,
                                 value=args.value,origin_ref=args.origin_ref)
                if args.save and output['status']=='CODE_CANDIDATE':
                    saved=cg.save(output,args.save)
                    output={'status':saved['status'],'file':saved['file'],
                            'pattern':args.pattern,'source_sha256':saved['source_sha256']}
            elif args.cmd=='thai-synthesize':
                from olgm.thai.synthesis import ThaiProgramSynthesizer
                raw=json.load(open(args.examples_json,encoding='utf-8'))
                output=ThaiProgramSynthesizer().synthesize(raw['train'],raw.get('validation'),
                              origin_ref=args.origin_ref,max_depth=args.depth)
                if args.save and output['status']=='CODE_CANDIDATE':
                    cg=SafeCodeGenerator(output_root=Path(__file__).resolve().parent/'generated',canti=rt.canti)
                    saved=cg.save(output,args.save)
                    output={'status':saved['status'],'file':saved['file'],
                            'source_sha256':saved['source_sha256'],
                            'program_steps':output['program_steps'],
                            'validation_accuracy':output['validation_accuracy']}
            elif args.cmd=='thai-code-pipeline':
                cg=SafeCodeGenerator(output_root=Path(__file__).resolve().parent/'generated',canti=rt.canti)
                output=cg.render_pipeline(args.steps,origin_ref=args.origin_ref)
                if args.save and output['status']=='CODE_CANDIDATE':
                    saved=cg.save(output,args.save)
                    output={'status':saved['status'],'file':saved['file'],
                            'source_sha256':saved['source_sha256'],'steps':args.steps}
            elif args.cmd=='thai-code-request':
                cg=SafeCodeGenerator()
                selected=cg.select(args.request)
                output=(cg.render(selected['pattern'],origin_ref=args.origin_ref)
                        if selected['status']=='MATCHED' else selected)
        elif args.cmd.startswith('control-'):
            from pathlib import Path
            from olgm.control import ResourceRegistry,ControlPlane,LocalComputer,ConnectorDispatcher
            reg=ResourceRegistry(rt.ms.db_path)
            ctl=ControlPlane(rt.ms.db_path,reg,rt.intent,rt.canti,rt.signatures,rt.audit)
            if args.cmd=='control-skills':
                from olgm.control.skills import BuiltinSkillExecutor
                output=BuiltinSkillExecutor.catalog()
            elif args.cmd=='control-install-skill':
                from olgm.control.skills import BuiltinSkillExecutor
                skill=BuiltinSkillExecutor(reg,ctl,rt.audit,rt.intent,rt.canti)
                output=skill.install(args.skill_id,args.origin_ref)
            elif args.cmd=='control-register':
                output=reg.register(args.resource_id,args.kind,args.display_name,args.provider,
                    [x.strip() for x in args.actions.split(',')],args.classification,
                    args.ownership_ref,args.source_ref,args.connection_state,
                    [x.strip() for x in args.targets.split(',') if x.strip()])
            elif args.cmd=='control-resources':output=reg.list(args.kind)
            elif args.cmd=='control-propose':
                output=ctl.propose(args.intent_id,args.intent_hash,args.resource_id,args.action,
                    json.loads(args.args_json),args.requested_by,args.idempotency_key)
            elif args.cmd=='control-receipt':
                output=ctl.receipt(args.plan_id,args.principal,args.expires_at,args.approval_ref)
            elif args.cmd=='control-approve':
                receipt=json.load(open(args.receipt_file,encoding='utf-8'))
                if 'receipt' in receipt:receipt=receipt['receipt']
                signature=Path(args.signature_file).read_text(encoding='utf-8').strip()
                output=ctl.approve(args.plan_id,receipt,signature)
            elif args.cmd=='control-enqueue':output=ctl.enqueue(args.plan_id,args.not_before,args.priority)
            elif args.cmd=='control-cancel':output=ctl.cancel(args.plan_id)
            elif args.cmd=='control-status':output=ctl.status(args.limit)
            elif args.cmd=='control-worker-step':
                # Explicit local opt-in only. ChatGPT connectors require an independent authenticated bridge.
                enable=(os.getenv('OLGM_ENABLE_DESKTOP')=='1' and
                        os.getenv('OLGM_INTERACTIVE_CONSENT')=='1' and not is_production())
                computer=LocalComputer(Path(os.getenv('OLGM_CAPTURE_DIR','control_captures')),
                                       enabled=enable)
                from olgm.control.skills import BuiltinSkillExecutor,SKILLS,installed_skill_id
                skill=BuiltinSkillExecutor(reg,ctl,rt.audit,rt.intent,rt.canti)
                handlers={installed_skill_id(k):(lambda action,args,idempotency_key,key=k:
                             skill.handler(key,action,args,idempotency_key)) for k in SKILLS}
                output=ctl.work_batch(ConnectorDispatcher(computer=computer,handlers=handlers),args.limit)
        elif args.cmd.startswith('value-'):
            from olgm.valueguard import ValueGuard,OWNER_EMAIL,THRESHOLD_THB,SmtpSender
            vg=ValueGuard(rt.ms.db_path,rt.audit)
            if args.cmd=='value-policy':
                output={'status':'POLICY_AVAILABLE','origin_email':OWNER_EMAIL,
                        'strictly_greater_than_thb':str(THRESHOLD_THB),
                        'exemption':'Origin-signed origin/family attestation only',
                        'delivery':'owner_email_first_then_external_user_notification',
                        'valuation':'forecast_not_certified','SMTP':'DISABLED_BY_DEFAULT'}
            elif args.cmd=='value-evaluate':
                with open(args.input,encoding='utf-8') as fh: request=json.load(fh)
                if 'evidence_exists' in request:raise ValueError('evidence_resolver_not_user_configurable')
                output=vg.evaluate(**request,evidence_exists=lambda ref:bool(rt.ms.get_evidence(ref)))
            elif args.cmd=='value-status':
                output=vg.case_status(args.case_id) if args.case_id else vg.pending()
            elif args.cmd=='value-exempt':
                with open(args.receipt_file,encoding='utf-8') as fh: receipt=json.load(fh)
                with open(args.signature_file,encoding='utf-8') as fh: signature=fh.read().strip()
                output=vg.register_exemption(args.subject,args.role,args.evidence_ref,receipt,signature)
            elif args.cmd=='value-dispatch':
                if not args.send:
                    output={'status':'DENIED','reason':'operator_must_pass_--send'}
                elif not rt.canti.check('notify_email','valueguard.origin_first')['allowed']:
                    output={'status':'DENIED','reason':'CANTI_notify_email_grant_required'}
                else:
                    output=vg.dispatch_next(SmtpSender.from_environment(),allowed=True)
        elif args.cmd.startswith('g06-'):
            from pathlib import Path
            from olgm.improve import SourceImprover
            improve=SourceImprover(Path(__file__).resolve().parent,rt.ms.db_path,rt.audit,rt.canti)
            if args.cmd=='g06-propose':output=improve.propose(args.intent)
            elif args.cmd=='g06-status':output=improve.status()
            elif args.cmd=='g06-receipt':output=improve.receipt_template(args.proposal_id,args.principal,args.action)
            elif args.cmd in ('g06-apply','g06-rollback'):
                receipt=json.load(open(args.receipt_file,encoding='utf-8'))
                signature=open(args.signature_file,encoding='utf-8').read().strip()
                if args.cmd=='g06-apply':output=improve.apply(args.proposal_id,receipt,signature)
                else:output=improve.rollback(args.proposal_id,receipt,signature)
        elif args.cmd in ('selflearn-v2-cycle','selflearn-v2-report'):

            from olgm.self_learn.orchestrator_v2 import HeavyDutyLearnerV2
            learner=HeavyDutyLearnerV2(rt.audit,tracker_path=args.state)
            if args.cmd=='selflearn-v2-cycle':
                output=learner.cycle(args.gens,args.batch,args.pop,intent=args.intent)
            else:output=learner.report()
        elif args.cmd=='production-preflight':
            from olgm.production import preflight
            output=preflight(rt,do_restore=not args.no_restore_drill)
            if args.output:
                with open(args.output,'w',encoding='utf-8') as f:
                    json.dump(output,f,ensure_ascii=False,indent=2)
        elif args.cmd=='s10-capture':
            from olgm.s10 import capture_pytest
            from pathlib import Path
            output=capture_pytest(Path(__file__).resolve().parent,args.output,args.timeout)
        elif args.cmd=='s10-evaluate':
            from olgm.s10 import evaluate
            keys=json.load(open(args.trusted_keys_json,encoding='utf-8')) if args.trusted_keys_json else None
            output=evaluate(rt,trace_id=args.trace_id,test_capture=args.test_capture,
                            evidence_manifest=args.manifest,evidence_root=args.evidence_root,
                            trusted_keys=keys)
            if args.output:
                with open(args.output,'w',encoding='utf-8') as f:
                    json.dump(output,f,ensure_ascii=False,indent=2)
        elif args.cmd=='init':
            output={'status':'INITIALIZED','db':rt.ms.db_path,'auto_grants':False,
                    'core0':'conceptual_boundary_not_accessible','model':rt.agent.observer.model.name}
        elif args.cmd=='audit-verify':
            ok,detail=rt.audit.verify();output={'status':'PASS' if ok else 'FAIL','detail':detail}
        elif args.cmd=='checkpoint-verify':output=rt.checkpoints.verify()
        elif args.cmd=='canonical-verify':output=rt.canonical.verify()
        elif args.cmd=='audit-anchor':
            if not rt.canti.check('anchor','audit.anchor')['allowed']:
                output={'status':'DENIED','reason':'CANTI_no_grant'}
            else:output=rt.audit.anchor(args.ref)
        elif args.cmd=='grant-dev':output=rt.canti.grant(args.scope,args.resource,'local_cli_operator',args.ttl)
        elif args.cmd=='revoke':output=rt.canti.revoke(args.grant_id)
        elif args.cmd in ('run','ask'):
            output=rt.process(args.question,actor=getattr(args,'actor','local_user'),
                     origin_ref=getattr(args,'origin_ref','external_declaration_ref'),
                     intent_tag=args.intent,task_type=getattr(args,'task_type','CHAT'),
                     seed_cids=getattr(args,'seed',[]),goal_cid=getattr(args,'goal',None),
                     enable_model=getattr(args,'enable_model',False))
        elif args.cmd=='observe':
            if not rt.canti.check('reason','agent.ask')['allowed']:
                output={'status':'DENIED','reason':'CANTI_no_reason_grant'}
            else:output=rt.agent.observer.observe(str(uuid.uuid4()),args.intent,args.text)
        elif args.cmd=='intent-lock':output=rt.intent.create(args.actor,args.origin_ref,args.text,task_type=args.task_type)
        elif args.cmd=='intent-revise':output=rt.intent.revise(args.intent_id,args.text,reason=args.reason,
                                                              expected_hash=args.expected_hash,actor=args.actor)
        elif args.cmd=='intent-proof':output=rt.intent.proof(args.intent_id,args.expected_hash)
        elif args.cmd=='canonical-init':output=rt.canonical.initialize(args.master_ref,args.master_sha256,args.actor)
        elif args.cmd=='policy-ref':output=rt.intent.register_policy_ref(args.policy_id,args.declaration_ref,args.sha256,args.five_axes_ref,args.version)
        elif args.cmd=='core-add':
            need_grant(rt,'meaning_space')
            output={'status':'ADDED_CANDIDATE_CORE','cid':rt.ms.add_core(args.cid,args.language,args.surface,
                                                                        definition=args.definition,origin_ref=args.origin_ref)}
        elif args.cmd=='edge-add':
            need_grant(rt,'meaning_space')
            output={'status':'ADDED_CANDIDATE_EDGE','edge_id':rt.ms.add_edge(args.edge_id,args.source,args.target,
                       args.type,context=args.context,origin_ref=args.origin_ref)}
        elif args.cmd=='graph-search':output={'seeds':rt.semantic.seed_candidates(args.text)}
        elif args.cmd=='graph-path':output=rt.semantic.candidate_paths(args.source,args.target)
        elif args.cmd=='evidence-add':
            need_grant(rt,'evidence')
            output={'status':'REGISTERED','ref':rt.ms.add_evidence(args.ref,args.type,args.content,source_url=args.source_url)}
        elif args.cmd=='claim-add':
            need_grant(rt,'evidence')
            output={'status':'CREATED','claim_id':rt.evidence.add_claim(args.text,args.class_name,origin_ref=args.origin_ref)}
        elif args.cmd=='claim-link':
            need_grant(rt,'evidence')
            output={'status':'LINKED','link_id':rt.evidence.link(args.claim_id,args.evidence_ref,args.type,args.excerpt,
                                                                assessed_by=args.assessor,assessment_method=args.method)}
        elif args.cmd=='claim-check':output=rt.evidence.v1_v7(args.claim_id)
        elif args.cmd=='edge-attest':
            need_grant(rt,'meaning_space')
            output=rt.semantic.attest_edge(args.edge_id,[args.evidence_ref],args.authority,args.reason)
        elif args.cmd=='plan':output=rt.actions.propose(args.intent_id,args.intent_hash,args.action,args.action,
                        json.loads(args.args_json),args.requested_by,args.idempotency_key)
        elif args.cmd=='approve':
            receipt=json.load(open(args.receipt_file,encoding='utf-8')) if args.receipt_file else None
            signature=open(args.signature_file,encoding='utf-8').read().strip() if args.signature_file else None
            output=rt.actions.approve(args.plan_id,args.by,args.approval_ref,
                        signed_receipt=receipt,signature_hex=signature)
        elif args.cmd=='key-enroll-dev':
            output=rt.signatures.enroll_public_key(args.principal,args.public_key_hex,args.authority,args.enrolled_by)
        elif args.cmd=='execute':output=rt.actions.execute(args.plan_id)
        elif args.cmd=='gis-point':
            from olgm.gis import BigMapGIS
            output=BigMapGIS().wgs84_to_indian_utm48(args.lat,args.lon)
        elif args.cmd=='gis-csv':
            from olgm.gis import BigMapGIS
            output=BigMapGIS().convert_csv(args.source_file,args.destination_file)
        elif args.cmd=='media-ingest':
            from olgm.multimodal import MultimodalIngest
            output=MultimodalIngest(rt.ms.db_path).ingest(args.file,args.origin_ref)
        elif args.cmd=='queue-intent':output=rt.queue.enqueue(args.intent_id,args.intent_hash,args.intent)
        elif args.cmd=='worker-step':output=rt.queue.run_steps(args.limit)
        elif args.cmd=='core0-attempt':output=rt.intent.refuse_core0_operation('cli',args.operation)
        elif args.cmd=='serve':
            from olgm.api import serve
            serve(rt.agent,args.host,args.port,integrated=rt,admin_token=os.getenv('OLGM_HTTP_TOKEN'))
            return 0
        else:raise AssertionError('unknown command')
    except (ValueError,TypeError,KeyError,PermissionError,sqlite_error()) as exc:
        output={'status':'DENIED' if isinstance(exc,PermissionError) else 'ERROR',
                'reason':str(exc),'exception':type(exc).__name__}
    print(json.dumps(output,ensure_ascii=False,indent=2))
    if args.cmd in ('s10-evaluate','production-preflight'):
        # CI must refuse a green release while independent proofs are missing.
        return 0 if output.get('overall')=='PASS' else 2
    return 1 if output.get('status') in ('FAIL','DENIED','BLOCKED','ERROR','ROOT_REENTRY','UNSUPPORTED','AMBIGUOUS','MATH_REJECTED') else 0


def sqlite_error():
    import sqlite3
    return sqlite3.Error


if __name__=='__main__':sys.exit(main())
