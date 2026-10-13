"""Independent fine floor/grid; original coarse classification remains immutable."""
from tools.diagnostic import l1_tlb_reach_analysis as coarse
_same=coarse._same
EVIDENCE='docs/reviews/evidence/2026-10-13-l1-tlb-fine'
PROTOCOL='docs/design/2026-10-13-l1-tlb-fine.md'
CONSUMER='tools/diagnostic/l1_tlb_fine_analysis.py'
DRIVER='tools/diagnostic/run_sm8650_l1_tlb_fine.py'
def expected(mode,epoch,phase):
 p=coarse.expected(mode,epoch,phase);p['version']=2
 if phase=='scan':p['nodes']=[32,46,47,48,49,50,51,52,56] if mode=='i' else [32,94,95,96,97,98,99,100,104]
 return p

def fine_onset(points):
 return coarse.onset([(n,0 if hi<=.001 else (1 if lo>=.005 else .05)) for n,lo,hi in points])

def audit_process(rr,p):
 a=coarse.audit_process(rr,p)
 if p['phase']=='scan':
  for c in a['curves']:c['onset']=fine_onset([(r['nodes'],*r['refill_range']) for r in c['residual']]);c['fine_floor']=dict(below=.001,above=.005)
  primary=[c for c in a['curves'] if c['role']&1];a['primary_supported']=all(c['onset']['status']=='localized' and c['walk_gate'] and c['cache_gate'] and c['aux_gate'] for c in primary)
 return a
