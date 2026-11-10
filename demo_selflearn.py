"""Usage: python examples/demo_selflearn.py --cycles 18 --output /tmp/demo_report.json"""
import argparse,json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from olgm.audit import AuditChain
from olgm.self_learn.orchestrator_v2 import HeavyDutyLearnerV2

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cycles',type=int,default=18)
    parser.add_argument('--output');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='olgm_g06_demo_') as tmp:
        audit=AuditChain(str(Path(tmp)/'audit.db'))
        learner=HeavyDutyLearnerV2(audit,tracker_path=str(Path(tmp)/'state.json'))
        for i in range(args.cycles):
            r=learner.cycle(n_generations=12,batch_size=10,pop_size=48)
            print(f"Gen {r['gen']:02d} task={r['intent']:15s} train={r['training_accuracy']:.3f} "
                  f"valid={r['validation_accuracy']:.3f} promoted={r['promoted']} "
                  f"growth={r['growth']['action']}")
        report=learner.report()
        ok,detail=audit.verify()
        report['audit_verified']=ok;report['audit_detail']=detail
        # Do not fabricate a PASS threshold; retain observed outcome.
        report['demonstrated_holdout_lift']=report['final_holdout_delta']>0
        print(json.dumps({'before':report['final_holdout_mean_before'],
            'after':report['final_holdout_mean_after'],'delta':report['final_holdout_delta'],
            'new_primitives':report['growth_count'],'audit_ok':ok,
            'interpretation':'synthetic symbolic benchmark, not general intelligence'},ensure_ascii=False,indent=2))
        if args.output:Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
