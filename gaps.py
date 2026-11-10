"""G-06 bounded capability gap identification. Does not fabricate unsupported code."""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import ast
import hashlib
import re

@dataclass(frozen=True)
class CapabilityGap:
    gap_id: str
    kind: str
    evidence: dict
    requested_at: str
    severity: str = 'medium'
    def to_dict(self): return asdict(self)

class GapDetector:
    def __init__(self, repo_path): self.root=Path(repo_path).resolve()
    def from_exception(self, exc):
        match=re.fullmatch(r'UnsupportedIntent:\s*([a-z][a-z0-9_]{0,47})',str(exc).strip())
        if not match: return None
        tag=match.group(1)
        return CapabilityGap(hashlib.sha256(f'unsupported_intent|{tag}'.encode()).hexdigest()[:20],
             'unsupported_intent',{'intent':tag,'exception_type':type(exc).__name__},
             datetime.now(timezone.utc).isoformat(),'high')
    def scan_not_implemented(self):
        gaps=[]
        for p in sorted((self.root/'olgm').glob('*.py')):
            try: tree=ast.parse(p.read_text(encoding='utf-8'))
            except (OSError,SyntaxError): continue
            for node in ast.walk(tree):
                if isinstance(node,ast.Raise) and isinstance(node.exc,ast.Call) and isinstance(node.exc.func,ast.Name) and node.exc.func.id=='NotImplementedError':
                    rel=str(p.relative_to(self.root));position=node.lineno
                    gaps.append(CapabilityGap(hashlib.sha256(f'{rel}:{position}'.encode()).hexdigest()[:20],
                        'not_implemented',{'file':rel,'line':position,'classification':'REQUIRES_REVIEW_NOT_AUTO_FILLED'},
                        datetime.now(timezone.utc).isoformat()))
        return gaps
