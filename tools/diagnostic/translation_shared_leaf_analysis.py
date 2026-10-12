"""Shared-memfd alias qualification; no retrospective steady CONT/HPA inference.

Contract docs/design/2026-10-12-translation-shared-leaf.md; preserves the actual
45-insn leaf filter contract and additionally proves canonical/alias page identity.
"""
from tools.diagnostic.translation_self_analysis import need,exact,BTF_SHA
from tools.diagnostic import translation_leaf_analysis as base
MODE='translation-shared-leaf'
PROTOCOL='docs/design/2026-10-12-translation-shared-leaf.md'
BUILD='docs/reviews/evidence/2026-10-12-translation-shared-leaf/build.json'
PLAN='docs/reviews/evidence/2026-10-12-translation-shared-leaf/plan.json'
CONSUMER='tools/diagnostic/translation_shared_leaf_analysis.py'
DRIVER='tools/diagnostic/run_sm8650_shared_leaf.py'
def audit_process(records,plan):
 need(type(records)is list and len(records)==1,'shared record coverage');d=records[0]
 if d.get('type')=='failure':return base.audit_process(records,plan)
 need(d.get('backing')=='shared-memfd' and type(plan)is dict and plan.get('backing')=='shared-memfd','shared requested backing')
 for key,alias in [('canonical_before','pagemap_before'),('canonical_after','pagemap_after')]:
  wires=d.get(key);need(type(wires)is list and len(wires)==2 and all(type(x)is int and 0<=x<1<<64 and x>>63 and not(x&(1<<62)) and x&((1<<55)-1) for x in wires),'canonical certificate')
  aw=d.get(alias);need(type(aw)is list and len(aw)==2 and all(type(x)is int for x in aw),'alias certificate')
  need([x&((1<<55)-1) for x in wires]==[x&((1<<55)-1) for x in aw],'canonical alias PFN mismatch')
 out=base.audit_process(records,plan)
 if out['status']=='SELF_LEAF_DESCRIPTOR_READ':out['status']='SHARED_LEAF_DESCRIPTOR_READ';out['observed_cont_scope']='shared-alias-read-to-write-entry-only'
 out['canonical_alias_pfn_match']=True
 return out
