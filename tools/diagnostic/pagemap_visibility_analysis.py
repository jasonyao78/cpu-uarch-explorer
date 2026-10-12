#!/usr/bin/env python3
"""Own-process nonzero PFN visibility, no public PFNs or capacity inference.

Frozen purpose: docs/design/2026-10-12-pagemap-visibility.md. Private raw keeps
absolute bits; public derived evidence carries counts and immutable raw SHA only.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
from tools.diagnostic.tlb_reach_analysis import pages
MODE='pagemap-visibility';DRIVER='tools/diagnostic/run_sm8650_pagemap_visibility.py';CONSUMER='tools/diagnostic/pagemap_visibility_analysis.py';PROTOCOL='docs/design/2026-10-12-pagemap-visibility.md';BUILD='docs/reviews/evidence/2026-10-12-pagemap-visibility/build.json';PLAN='docs/reviews/evidence/2026-10-12-pagemap-visibility/plan.json'
def plan():return [dict(type='config',version=1,probe=MODE,pool_pages=1048576,family_nodes=16,snapshots=2,page_set_seed=271),dict(type='selection',page_ids=sorted({p for shape in ('dense','spaced','balanced-random') for p in pages(shape,16)}))]
def validate_plan(p):_require(_same(p,plan()),'pagemap actual plan')
def conditions():return [dict(name=f'epoch-{e}',args=['--run']) for e in range(3)]
def audit_process(rr,registered):
 """Zero PFN stays opaque. Endpoint stability is not continuous residency."""
 validate_plan(registered);want=plan();pp=want[1]['page_ids'];_require(type(rr) is list and len(rr)==5+2*len(pp),'pagemap coverage');_require(_same(rr[:2],want),'pagemap config/selection');_fields(rr[2],dict(type='runtime',cpu=7),'pagemap CPU');b=rr[2].get('base');_require(type(b) is int and b>0 and b%4096==0 and b<=2**64-1048576*4096,'pagemap base')
 for i,stage in ((3,'before'),(len(rr)-1,'after')):_fields(rr[i],dict(type='backing',stage=stage,base_page_bytes=4096,anon_huge_kb=0),'pagemap backing')
 snap=[];present=[];swapped=[]
 for i,stage in enumerate(('before','after')):
  ss=[]
  for p,r in zip(pp,rr[4+i*len(pp):4+(i+1)*len(pp)]):
   _fields(r,dict(type='pagemap',stage=stage,page_id=p),'pagemap sample identity');v=r.get('entry');_require(type(v) is int and 0<=v<2**64,'pagemap wire type');ss.append(v&((1<<55)-1));present.append(bool(v&(1<<63)));swapped.append(bool(v&(1<<62)))
  snap.append(ss)
 nonzero=sum(v!=0 for v in snap[0]);unique=len(set(snap[0]));changed=sum(x!=y for x,y in zip(*snap));stable=all(present) and not any(swapped) and all(v!=0 for s in snap for v in s) and unique==len(pp) and len(set(snap[1]))==len(pp) and changed==0
 status='visible-stable' if stable else 'opaque-or-zero' if all(v==0 for s in snap for v in s) else 'partial-or-unstable'
 return dict(status=status,pages=len(pp),snapshots=2,nonzero=nonzero,unique_pfns=unique,changed_pfns=changed,present=sum(present),swapped=sum(swapped),pfn_contiguous_geometry_certified=False,pte_cont_state='UNKNOWN')
def audit_raw(path):
 inventory={'manifest.json','driver.py','consumer.py','environment-policy.json','initial-environment.json','final-environment.json'}|{c['name']+s for c in conditions() for s in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')};_require({p.name for p in path.iterdir()}==inventory and all(p.is_file() for p in path.iterdir()),'pagemap inventory');m=json.loads((path/'manifest.json').read_text());_fields(m,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,build_evidence_path=BUILD,plan_path=PLAN,protocol_path=PROTOCOL,consumer_path=CONSUMER),'pagemap manifest');_require(_same(m.get('conditions'),conditions()) and type(m.get('results')) is list and len(m['results'])==3,'pagemap conditions')
 blob=lambda h,p:subprocess.check_output(['git','show',h+':'+p],cwd=ROOT);sha=lambda b:hashlib.sha256(b).hexdigest();head=m['source_head']
 for p,k in ((DRIVER,'driver_sha256'),(CONSUMER,'consumer_sha256'),(PROTOCOL,'protocol_sha256'),(BUILD,'build_evidence_sha256'),(PLAN,'plan_sha256')):_require(sha(blob(head,p))==m[k],'pagemap launch dependency '+p)
 for f,k in (('driver.py','driver_sha256'),('consumer.py','consumer_sha256')):_require(sha((path/f).read_bytes())==m[k],'pagemap saved '+f)
 b=json.loads(blob(head,BUILD));p=json.loads(blob(head,PLAN));validate_plan(p);_require(b['source_commit']==m['binary_source_head'] and b['binaries']['pagemap_visibility']==m['binary_sha256'] and b['plan_sha256']==m['plan_sha256'],'pagemap binary binding')
 for f,d in b['source_sha256'].items():_require(sha(blob(head,f))==d and sha(blob(m['binary_source_head'],f))==d,'pagemap source '+f)
 from tools.diagnostic.analyze_long_load import audit_environment
 policy=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'))['environment_profiles']['charging-thermal']['measurement_environment'];policy['preconditions']['cpufreq_governor']='walt';env={p.name:json.loads(p.read_text()) for p in path.glob('*-environment.json')};audit_environment(env,json.loads((path/'environment-policy.json').read_text()),policy);out=[]
 for c,r in zip(conditions(),m['results']):
  _fields(r,dict(name=c['name'],exit_code=0,timed_out=False),'pagemap result');f=path/(c['name']+'.stdout.jsonl');_require(sha(f.read_bytes())==r['stdout_sha256'] and (path/(c['name']+'.stderr.log')).read_bytes()==b'','pagemap stdout/stderr');out.append(dict(epoch=c['name'],**audit_process([json.loads(l) for l in f.read_text().splitlines()],p)))
 return dict(mode=MODE,raw_directory=path.name,source_branch=m['source_branch'],source_head=head,binary_source_head=m['binary_source_head'],binary_sha256=m['binary_sha256'],manifest_sha256=sha((path/'manifest.json').read_bytes()),processes=3,rows=out,visible=all(r['status']=='visible-stable' for r in out),all_raw_sha256={p.name:sha(p.read_bytes()) for p in sorted(path.iterdir())},physical_capacity_certified=False)
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv);r=audit_raw(a.raw);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(visible=r['visible'],processes=3,rows=r['rows'])))
if __name__=='__main__':main()
