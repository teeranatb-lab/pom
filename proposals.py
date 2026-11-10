"""Known-pattern bounded code proposals. Generated edits have an exact allowlist."""
from dataclasses import dataclass, asdict
from pathlib import Path
import ast
import difflib
import hashlib
import json
import re

# Proposed method routes only: this does not implement a new cognitive operator.
INTENT_TEMPLATES={
    'compare':[3,10,19], 'classify':[3,4,19], 'predict':[8,9,17,19],
    'explain':[6,9,14,19], 'diagnose':[6,9,16,19], 'optimize':[6,15,17,19],
    'design':[11,14,15,19], 'verify':[2,7,10,19], 'summarize':[3,14,19],
    'translate':[3,13,19], 'audit':[2,10,18,19], 'forecast':[8,16,17,19],
    'simulate':[6,17,19], 'evaluate':[6,10,18,19], 'research':[2,8,10,19],
    'plan':[6,15,17,19], 'debug':[2,6,9,18,19], 'map':[2,5,19],
    'calculate':[6,7,19], 'reason':[6,7,14,19], 'connect':[3,13,15,19],
    'synthesize':[3,14,15,19], 'decide':[6,10,19], 'learn':[8,14,18,19],
    'review':[3,10,18,19], 'monitor':[2,16,18,19], 'transform':[6,12,14,19],
    'repair':[6,9,14,19], 'generate':[11,14,19], 'discover':[2,9,11,19],
}
ALLOWED_TARGETS=frozenset({'olgm/methods.py','olgm/g06_capabilities.json'})

def sha_bytes(data): return hashlib.sha256(data).hexdigest()
def version_next(version):
    if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('bad_version')
    a,b,c=(int(x) for x in version.split('.'))
    return f'{a}.{b}.{c+1}'

def current_mapping(source):
    tree=ast.parse(source)
    nodes=[x for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='INTENT_TO_METHODS' for t in x.targets)]
    if len(nodes)!=1 or not isinstance(nodes[0].value,ast.Dict):raise ValueError('mapping_missing_or_invalid')
    mapping=ast.literal_eval(nodes[0].value)
    if not isinstance(mapping,dict) or not all(isinstance(k,str) and isinstance(v,list) and all(type(n) is int and 1<=n<=19 for n in v) for k,v in mapping.items()):
        raise ValueError('mapping_not_static')
    return mapping,nodes[0].value

@dataclass(frozen=True)
class FileChange:
    path:str
    old_sha256:str|None
    new_sha256:str
    patched_text:str
    diff:str
    def to_dict(self):return asdict(self)

@dataclass(frozen=True)
class CodeChangeProposal:
    proposal_id:str
    gap_id:str
    intent:str
    rationale:str
    old_version:str
    new_version:str
    fingerprint:str
    files:list[FileChange]
    tests:list[str]
    limits:list[str]
    def to_dict(self):return asdict(self)

class ProposalGenerator:
    def __init__(self,repo_path):self.root=Path(repo_path).resolve()
    def generate(self,gap,version):
        if gap.kind!='unsupported_intent':return None
        intent=gap.evidence['intent']
        if intent not in INTENT_TEMPLATES:return None
        path=self.root/'olgm'/'methods.py'
        original=path.read_text(encoding='utf-8')
        mapping,node=current_mapping(original)
        if intent in mapping:return None
        lines=original.splitlines(keepends=True)
        close_line=node.end_lineno-1
        line=lines[close_line]
        bracepos=line.rfind('}',0,node.end_col_offset+1)
        if bracepos<0:raise ValueError('mapping_closing_brace_missing')
        # Insert immediately before the literal-closing brace; preserve all old statements.
        addition=f'\n    {intent!r}: {INTENT_TEMPLATES[intent]!r},\n'
        before=line[:bracepos].rstrip()
        if before and not before.endswith(('{', ',')):before+=','
        patched=''.join(lines[:close_line]+[before+addition+line[bracepos:]]+lines[close_line+1:])
        new_mapping,_=current_mapping(patched)
        if len(new_mapping)!=len(mapping)+1 or any(new_mapping[k]!=v for k,v in mapping.items()) or new_mapping[intent]!=INTENT_TEMPLATES[intent]:
            raise ValueError('unsafe_or_nonappend_mapping')
        registry_path=self.root/'olgm'/'g06_capabilities.json'
        if registry_path.exists():
            registry_old=registry_path.read_text(encoding='utf-8')
            reg=json.loads(registry_old)
            if not isinstance(reg,dict) or reg.get('scope')!='intent_routing_only' or not isinstance(reg.get('entries'),dict):raise ValueError('invalid_registry')
        else:
            registry_old=None
            reg={'scope':'intent_routing_only','entries':{}}
        if intent in reg['entries']:raise ValueError('registry_conflict')
        reg['entries'][intent]={'methods':INTENT_TEMPLATES[intent], 'version':version_next(version),'proof':'ROUTING_TEST_REQUIRED'}
        registry_new=json.dumps(reg,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
        def change(rel,old,new):
            diff=''.join(difflib.unified_diff((old or '').splitlines(True),new.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
            return FileChange(rel,sha_bytes(old.encode()) if old is not None else None,sha_bytes(new.encode()),new,diff)
        files=[change('olgm/methods.py',original,patched),change('olgm/g06_capabilities.json',registry_old,registry_new)]
        fingerprint=sha_bytes(json.dumps({'gap':gap.gap_id,'version':version,'files':[(f.path,f.old_sha256,f.new_sha256) for f in files]},sort_keys=True).encode())
        return CodeChangeProposal(fingerprint[:20],gap.gap_id,intent,
            f'Append deterministic method route for intent {intent!r} (no novel synthesis)',
            version,version_next(version),fingerprint,files,
            ['python -m pytest -q -ra','route mapping regression','new intent routing assertion'],
            ['No novel code synthesis','An added route is NOT proven answer quality','No source mutation without separate approval'])
    def validate(self,proposal):
        """Regenerate trusted proposal from its requested intent; reject modified stored bytes."""
        from .gaps import GapDetector
        gap=GapDetector(self.root).from_exception(ValueError('UnsupportedIntent: '+proposal['intent']))
        if gap is None:raise ValueError('invalid_intent')
        expected=self.generate(gap,proposal['old_version'])
        if expected is None or expected.to_dict()!=proposal:raise ValueError('proposal_drift_or_tamper')
        if {f['path'] for f in proposal['files']}!=ALLOWED_TARGETS:raise ValueError('file_allowlist_violation')
        return expected
