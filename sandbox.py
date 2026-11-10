"""Trusted-template regression workspace, NOT a security isolation sandbox.

Only trusted built-in deterministic source edits are ever executed by this runner.
Do not run user/LLM-generated code here. That requires OS/container isolation.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

# Safety: the G-06 test itself cannot invoke the entire regression suite recursively.
# A separate top-level full pytest run is required for S-10; this subset checks
# the directly affected routes and system governance in each patch workspace.
G06_REGRESSION_TARGETS = (
    'tests/test_acceptance_t06_t31.py',
    'tests/test_integrated_pipeline.py',
    'tests/test_s10_release_gate.py',
    'tests/test_production_preflight_v09.py',
    'tests/test_control_plane_v10.py',
)

class SandboxRunner:
    def __init__(self,repo_path,timeout=120):
        self.root=Path(repo_path).resolve()
        self.timeout=timeout

    def create(self):
        tmp=tempfile.TemporaryDirectory(prefix='olgm_g06_trusted_workspace_')
        dst=Path(tmp.name)
        # Recreate the importable project tree, including nested self_learn modules.
        for subtree in ('olgm','tests'):
            for p in sorted((self.root/subtree).rglob('*.py')):
                if p.is_symlink() or any(parent.is_symlink() for parent in p.parents if parent!=self.root):
                    raise ValueError('symlink_source_forbidden')
                rel=p.relative_to(self.root)
                (dst/rel).parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(p,dst/rel)
        for name in ('runtime.py','pytest.ini'):
            p=self.root/name
            if p.is_symlink():raise ValueError('symlink_source_forbidden')
            if p.exists():shutil.copy2(p,dst/name)
        return tmp,dst

    def apply(self,dst,proposal):
        for entry in proposal['files']:
            if entry['path'] not in ('olgm/methods.py','olgm/g06_capabilities.json'):
                raise ValueError('untrusted_patch_target')
            path=dst/entry['path'];path.write_text(entry['patched_text'],encoding='utf-8')

    def _run(self,cmd,dst):
        env=os.environ.copy()
        for k in ('OLGM_BASE','OLGM_MODEL','OLGM_CKPT_BEFORE','OLGM_CKPT_AFTER','OLGM_BENCH_BEFORE','OLGM_BENCH_AFTER','OLGM_DB','OLGM_ANCHOR','OLGM_ANCHOR_KEY'):
            env.pop(k,None)
        env['PYTHONDONTWRITEBYTECODE']='1'
        env['OLGM_G06_SANDBOX_TEST']='1'
        try:
            p=subprocess.run(cmd,cwd=dst,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                 text=True,timeout=self.timeout,stdin=subprocess.DEVNULL)
            return {'ok':p.returncode==0,'returncode':p.returncode,'output_tail':p.stdout[-1800:]}
        except subprocess.TimeoutExpired:
            return {'ok':False,'returncode':124,'output_tail':'TIMEOUT'}

    def assess(self,proposal,old_mapping,expected_methods):
        tmp,dst=self.create()
        try:
            baseline=self._run([sys.executable,'-m','pytest','-q','-ra',*G06_REGRESSION_TARGETS],dst)
            self.apply(dst,proposal)
            patched=self._run([sys.executable,'-m','pytest','-q','-ra',*G06_REGRESSION_TARGETS],dst)
            # On the patched copied source, assert all pre-existing routes still match,
            # and the intended new route is actually imported and selected.
            script='''import json
from olgm.methods import INTENT_TO_METHODS,select_methods
old=json.loads(__import__('os').environ['OLGM_G06_OLD'])
expected=json.loads(__import__('os').environ['OLGM_G06_EXPECTED'])
assert all(INTENT_TO_METHODS[k]==v for k,v in old.items())
assert len(INTENT_TO_METHODS)==len(old)+1
intent=__import__('os').environ['OLGM_G06_INTENT']
assert INTENT_TO_METHODS[intent]==expected
chosen=select_methods(intent)
assert chosen[0]==1 and chosen[-1]==19
assert all(m in chosen for m in expected)
print('ROUTE_VERIFIED')'''
            # Controlled inputs from trusted dict; no shell execution.
            env=os.environ.copy();env['OLGM_G06_OLD']=json.dumps(old_mapping)
            env['OLGM_G06_EXPECTED']=json.dumps(expected_methods)
            env['OLGM_G06_INTENT']=proposal['intent']
            env['PYTHONDONTWRITEBYTECODE']='1'
            try:
                p=subprocess.run([sys.executable,'-c',script],cwd=dst,env=env,
                       stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=self.timeout)
                route={'ok':p.returncode==0,'returncode':p.returncode,'output_tail':p.stdout[-1200:]}
            except subprocess.TimeoutExpired:
                route={'ok':False,'returncode':124,'output_tail':'TIMEOUT'}
            return {'ok':baseline['ok'] and patched['ok'] and route['ok'],
                    'baseline':baseline,'patched':patched,'routing':route,
                    'meaning':'Trusted template routing + regression, not independent cognitive improvement',
                    'external_isolation':False}
        finally:tmp.cleanup()
