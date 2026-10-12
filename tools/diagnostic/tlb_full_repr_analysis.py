#!/usr/bin/env python3
"""Same physical demand graph, different stored next-pointer representation.

Frozen: docs/design/2026-10-12-tlb-full-pointer-representation.md. Exact raw
encoded graph and PFNs precede statistics; no physical entries or unique DMP attribution.
"""
import argparse,hashlib,json,statistics as st,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
from tools.diagnostic.tlb_alias_analysis import permutation,pages,layout_mapping,geometry as alias_geometry,check_wire
MODE='tlb-full-pointer-representation';PROTOCOL='docs/design/2026-10-12-tlb-full-pointer-representation.md';BUILD='docs/reviews/evidence/2026-10-12-tlb-full-pointer-representation/build.json';PLAN='docs/reviews/evidence/2026-10-12-tlb-full-pointer-representation/plan.json';DRIVER='tools/diagnostic/run_sm8650_tlb_full_repr.py';CONSUMER='tools/diagnostic/tlb_full_repr_analysis.py'
GRID=(1024,1792,2048);SHAPES=('dense','spaced','balanced-random');ORDERS=('random','reverse-random');HIGH_MASK=0x00a5000000000000;MASK=0x9e3779b97f4a7c15;REPRESENTATIONS=('plain','xor-high','xor-full')
def config(reverse):return dict(type='config',version=1,probe=MODE,pool_pages=1048576,page_set_seed=271,order_seed=137,n_grid=list(GRID),load_budget=1048576,rounds=3,events=[17,8,5,52,33108,33109],pmu_type=8,reverse=reverse,cells=55,windows=165,decode_loop_instructions=4)
def plan(reverse):
 _require(type(reverse) is bool,'repr reverse type')
 from tools.diagnostic.tlb_alias_analysis import plan as alias_plan
 cc=[]
 for x in alias_plan(False)[1:]:
  if not x['n']:cc.append(dict(x,representation='none',mask=0));continue
  if x['n'] not in GRID:continue
  for mode in REPRESENTATIONS:cc.append(dict(x,cell=x['cell']+'-'+mode,representation=mode,mask={'plain':0,'xor-high':HIGH_MASK,'xor-full':MASK}[mode]))
 if reverse:cc.reverse()
 return [config(reverse),*[dict(c,position=i) for i,c in enumerate(cc)]]
def validate_plan(p):_require(_same(p,dict(forward=plan(False),reverse=plan(True))),'repr actual plan mismatch')
def geometry(c,bases):return alias_geometry(c,bases)
def graph(c,base):
 pp=pages(c['shape'],c['n']) if c['n'] else [];oo=list(permutation(c['n'],137)) if c['n'] else []
 if c['order']=='reverse-random':oo.reverse()
 node=lambda i:base+pp[i]*4096+64*(i%64);words=[0]*c['n']
 for j,i in enumerate(oo):words[i]=node(oo[(j+1)%c['n']])^c['mask']
 return dict(cell=c['cell'],head=node(oo[0]) if oo else 0,stored_words=words)
def sample_check(s,c,t):
 _fields(s,dict(type='round',cell=c['cell'],position=c['position'],round=t,head_returned=True),'repr sample identity');_require(type(s.get('enabled')) is int and 0<s['enabled']<2**64 and type(s.get('running')) is int and s['running']==s['enabled'],'repr mux/time');v=s.get('counts');_require(type(v) is list and len(v)==6 and all(type(x) is int and 0<=x<2**64 for x in v),'repr counts')
 if c['n']:_require(v[0]>0 and abs(v[1]-4*c['loads'])<=max(1000,.01*4*c['loads']),'repr IR/core loop')
def audit_process(records,reverse,registered):
 """Exact shared-PFN identity before and after; published rows remove addresses."""
 validate_plan(registered);_require(type(records) is list and len(records)==608,'alias raw coverage');_require(_same(records[0],config(reverse)),'alias config');pmu=records[1];_fields(pmu,dict(type='pmu'),'alias PMU');ids=pmu.get('ids');_require(type(ids) is list and len(ids)==6 and all(type(i) is int and 0<i<2**64 for i in ids) and len(set(ids))==6,'alias kernel IDs')
 backing=records[2];_fields(backing,dict(type='physical-backing',backing_pages=2560,pool_pages=1048576,pte_cont_state='UNKNOWN'),'alias physical backing');bases=backing.get('arena_bases');_require(type(bases) is list and len(bases)==3 and all(type(b) is int and b>0 and b%1048576==0 and b<=2**64-1048576*4096 for b in bases),'alias arena alignment');cb=backing.get('canonical_base');_require(type(cb) is int and cb>0 and cb%4096==0 and cb<=2**64-2560*4096,'alias canonical base');regions=[(b,b+1048576*4096) for b in bases]+[(cb,cb+2560*4096)];_require(all(e1<=b2 or e2<=b1 for i,(b1,e1) in enumerate(regions) for b2,e2 in regions[i+1:]),'alias owned overlap');pfns=backing.get('canonical_pfns');_require(type(pfns) is list and len(pfns)==2560 and all(type(p) is int and 0<p<2**55 for p in pfns) and len(set(pfns))==2560,'alias canonical PFN visibility/identity');check_wire(backing.get('canonical_entries'),pfns);out=[];cursor=3
 for c in plan(reverse)[1:]:
  _require(_same(records[cursor],c),'alias cell identity');cursor+=1;g=records[cursor];cursor+=1;_require(_same(g,geometry(c,bases)),'alias geometry')
  for stage in ('before','after'):
   _fields(records[cursor],dict(type='backing',cell=c['cell'],stage=stage,kernel_page_kb=4,mmu_page_kb=4,anon_huge_kb=0,shmem_pmd_kb=0,file_pmd_kb=0),'alias physical page policy');cursor+=1;cert=records[cursor];check_wire(cert.get('pagemap_entries'),pfns[:c['n']]);_require(_same(cert,dict(type='pfn-certificate',cell=c['cell'],stage=stage,alias_pfns=pfns[:c['n']],pagemap_entries=cert['pagemap_entries'])),'alias PFN conflict/masked/type');cursor+=1;_require(_same(records[cursor],dict(graph(c,bases[SHAPES.index(c['shape'])] if c['n'] else 0),type='graph-certificate',stage=stage)),'repr stored graph/decode conflict')
   if c['representation']=='xor-full':
    for word in records[cursor]['stored_words']:
     decoded=word^c['mask']
     for width in (39,48,56):
      bits=(1<<width)-1;_require((word&bits)!=(decoded&bits) and (word&bits&~63)!=(decoded&bits&~63),'repr actual low-address intervention')
   cursor+=1
  samples=[]
  for t in range(3):ss=records[cursor];cursor+=1;sample_check(ss,c,t);samples.append(ss)
  relative=dict(g);base=bases[SHAPES.index(c['shape'])] if c['n'] else 0;relative['l3_parent_ids']=[p-(base//4096>>9) for p in g['l3_parent_ids']];out.append(dict(c,geometry=relative,pmu_ids=ids,samples=samples,physical_nodes_verified=c['n'],stored_graph_verified=c['n'],low_address_intervention_verified=c['n'] if c['representation']=='xor-full' else 0))
 return out

def ratio(v,loads):return dict(cycles_per_load=v[0]/loads,l1_refills_per_load=v[2]/loads,walks_per_load=v[3]/loads,l1_hw_prefetch_per_load=v[4]/loads,l2_hw_prefetch_per_load=v[5]/loads)
def analyze(run):
 """Per-epoch/order difference of differences; all raw windows stay visible."""
 _fields(run,dict(mode=MODE,processes=3),'repr matrix');rows=run.get('rows');_require(type(rows) is list and len(rows)==165,'repr rows');cursor=0;by={}
 for e in range(3):
  for c in plan(bool(e%2))[1:]:
   r=rows[cursor];cursor+=1;_fields(r,dict(c,epoch=f'epoch-{e}',physical_nodes_verified=c['n'],stored_graph_verified=c['n'],low_address_intervention_verified=c['n'] if c['representation']=='xor-full' else 0),'repr identity certificates');_require(type(r.get('samples')) is list and len(r['samples'])==3,'repr sample coverage')
   for t,s in enumerate(r['samples']):sample_check(s,c,t)
   by[e,c['cell']]=r
 points=[];checks=[];windows=[];lookup={};tapchecks=[]
 for e in range(3):
  bg=[st.median(s['counts'][j] for s in by[e,'floor']['samples']) for j in range(6)]
  for c in plan(bool(e%2))[1:]:
   if not c['n']:continue
   ss=by[e,c['cell']]['samples'];sums=[sum(s['counts'][j] for s in ss) for j in range(6)];p=dict(epoch=e,**c,**ratio(sums,3*c['loads']));points.append(p);lookup[e,c['shape'],c['order'],c['n'],c['representation']]=p
   for s in ss:
    v=s['counts'];gates=dict(cycle_background=bg[0]<=.01*v[0],translation_background=all(bg[j]<=.001*c['loads'] for j in (2,3)),l1_translation_pressure=.75*c['loads']<=v[2]<=1.25*c['loads']);checks.append(dict(epoch=e,cell=c['cell'],round=s['round'],gates=gates,passed=all(gates.values())));tapchecks.append(dict(epoch=e,cell=c['cell'],round=s['round'],passed=all(bg[j]<=.001*c['loads'] for j in (4,5))));windows.append(dict(epoch=e,cell=c['cell'],round=s['round'],counts=v,ratios=ratio(v,c['loads']),corrected_ratios=ratio([v[j]-bg[j] for j in range(6)],c['loads'])))
 comparisons=[];geometric=[];changes=[]
 for shape in SHAPES:
  for n in GRID:
   for representation in ('xor-high','xor-full'):
    changes.append(dict(shape=shape,n=n,representation=representation,deltas=[dict(epoch=e,order=o,**{key:lookup[e,shape,o,n,representation][key]-lookup[e,shape,o,n,'plain'][key] for key in ratio([0]*6,1)}) for e in range(3) for o in ORDERS]))
   if shape=='dense':continue
   for mode in REPRESENTATIONS:
    d=[dict(epoch=e,order=o,delta=lookup[e,shape,o,n,mode]['walks_per_load']-lookup[e,'dense',o,n,mode]['walks_per_load']) for e in range(3) for o in ORDERS];geometric.append(dict(shape=shape,n=n,representation=mode,deltas=d))
   d=[dict(epoch=e,order=o,delta=(lookup[e,shape,o,n,'xor-full']['walks_per_load']-lookup[e,'dense',o,n,'xor-full']['walks_per_load'])-(lookup[e,shape,o,n,'plain']['walks_per_load']-lookup[e,'dense',o,n,'plain']['walks_per_load'])) for e in range(3) for o in ORDERS];vv=[x['delta'] for x in d];comparisons.append(dict(shape=shape,n=n,deltas=d,range=[min(vv),max(vv)],numeric_replicated=all(v>=.10 for v in vv) or all(v<=-.10 for v in vv)))
 auxiliary=[]
 for shape in ('spaced','balanced-random'):
  for n in GRID:
   for first,second in (('plain','xor-high'),('xor-high','xor-full')):
    d=[dict(epoch=e,order=o,delta=(lookup[e,shape,o,n,second]['walks_per_load']-lookup[e,'dense',o,n,second]['walks_per_load'])-(lookup[e,shape,o,n,first]['walks_per_load']-lookup[e,'dense',o,n,first]['walks_per_load'])) for e in range(3) for o in ORDERS];auxiliary.append(dict(shape=shape,n=n,first=first,second=second,deltas=d,range=[min(x['delta'] for x in d),max(x['delta'] for x in d)]))
 bgok=all(x['passed'] for x in checks);base=any(x['representation']=='plain' and x['n']>=1792 and all(v['delta']>=.10 for v in x['deltas']) for x in geometric)
 for c in comparisons:c['replicated']=bgok and base and c['numeric_replicated']
 small=all(abs(x['delta'])<.10 for c in comparisons for x in c['deltas']);verdict='INCONCLUSIVE' if not bgok else 'BASE_GEOMETRY_NOT_REPLICATED' if not base else 'GEOMETRY_CONTRAST_REPRESENTATION_SENSITIVE' if any(c['replicated'] for c in comparisons) else 'GEOMETRY_CONTRAST_NOT_CHANGED_AT_DETECTION_SCALE' if small else 'INCONCLUSIVE';tapok=all(x['passed'] for x in tapchecks);observed=any(w['counts'][j]>0 for w in windows for j in (4,5));tapstatus='INCOMPUTABLE' if not tapok else 'PREFETCH_COUNTS_OBSERVED' if observed else 'NO_PREFETCH_COUNTS_IN_MATRIX'
 return dict(mode=MODE,windows=495,verdict=verdict,background_passed=bgok,base_geometry_replicated=base,epoch_points=points,window_ratios=windows,background_checks=checks,prefetch_background_checks=tapchecks,prefetch_status=tapstatus,comparisons=comparisons,auxiliary_comparisons=auxiliary,geometric=geometric,representation_changes=changes,physical_entries_certified=False,dmp_attributed=False,pte_cont_state='UNKNOWN',pfn_state='MATCHED_DATA_PAGES',naming_limit='same physical demand graph; storage and decode resource/speculation can change, no unique DMP, descriptor or capacity attribution')

def conditions():return [dict(name=f'epoch-{e}',args=['--run',*(['--reverse'] if e%2 else [])]) for e in range(3)]

def audit_raw(path):
 """Exact inventory, committed launch/binary/plan, environment and real records."""
 expected={'manifest.json','driver.py','consumer.py','environment-policy.json','initial-environment.json','final-environment.json'}|{f'epoch-{e}'+s for e in range(3) for s in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')};_require({p.name for p in path.iterdir()}==expected and all(p.is_file() for p in path.iterdir()),'reach raw inventory')
 m=json.loads((path/'manifest.json').read_text());_fields(m,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,build_evidence_path=BUILD,protocol_path=PROTOCOL,plan_path=PLAN,consumer_path=CONSUMER),'reach manifest identity');_require(_same(m.get('conditions'),conditions()) and type(m.get('results')) is list and len(m['results'])==3,'reach requested coverage')
 blob=lambda ref,p:subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT);sha=lambda b:hashlib.sha256(b).hexdigest();head=m['source_head']
 for file,key in ((DRIVER,'driver_sha256'),(CONSUMER,'consumer_sha256'),(PROTOCOL,'protocol_sha256'),(BUILD,'build_evidence_sha256'),(PLAN,'plan_sha256')):_require(sha(blob(head,file))==m[key],'reach launch SHA '+file)
 _require(sha((path/'driver.py').read_bytes())==m['driver_sha256'],'reach saved driver');_require(sha((path/'consumer.py').read_bytes())==m['consumer_sha256'],'reach saved consumer');build=json.loads(blob(head,BUILD));registered=json.loads(blob(head,PLAN));validate_plan(registered)
 _require(build['binaries']['tlb_full_repr']==m['binary_sha256'] and build['source_commit']==m['binary_source_head'] and build['plan_sha256']==m['plan_sha256'],'reach binary/source/plan binding')
 for p,digest in build['source_sha256'].items():_require(sha(blob(head,p))==digest and sha(blob(m['binary_source_head'],p))==digest,'reach dependency SHA '+p)
 from tools.diagnostic.analyze_long_load import audit_environment
 profile=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'));policy=profile['environment_profiles']['charging-thermal']['measurement_environment'];policy['preconditions']['cpufreq_governor']='walt';env={p.name:json.loads(p.read_text()) for p in path.glob('*-environment.json')};audit_environment(env,json.loads((path/'environment-policy.json').read_text()),policy)
 rows=[];mapping=[]
 for e,(r,c) in enumerate(zip(m['results'],conditions())):
  _fields(r,dict(name=c['name'],exit_code=0,timed_out=False),'reach result order/status');f=path/(c['name']+'.stdout.jsonl');_require(sha(f.read_bytes())==r['stdout_sha256'] and (path/(c['name']+'.stderr.log')).read_bytes()==b'','reach stdout/stderr binding');records=[json.loads(l) for l in f.read_text().splitlines()];rows.extend(dict(row,epoch=c['name']) for row in audit_process(records,bool(e%2),registered));mapping.append(dict(epoch=e,physical_backing_pages=2560,aliases=3,canonical_nonzero_unique=True,absolute_addresses_public=False))
 result=dict(mode=MODE,processes=3,source_branch=m['source_branch'],source_head=head,binary_source_head=m['binary_source_head'],binary_sha256=m['binary_sha256'],raw_directory=path.name,manifest_sha256=sha((path/'manifest.json').read_bytes()),max_cpu_c_range=[min(v['snapshot']['thermal']['max_cpu_c'] for v in env.values()),max(v['snapshot']['thermal']['max_cpu_c'] for v in env.values())],mapping=mapping,rows=rows)
 return result,{p.name:sha(p.read_bytes()) for p in sorted(path.iterdir())}
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--summary-output',type=Path,required=True);a=p.parse_args(argv);run,hashes=audit_raw(a.raw);result=analyze(run);s=json.dumps(run,indent=2,allow_nan=False)+'\n';result.update(data_origin='device-raw',input_sha256=hashlib.sha256(s.encode()).hexdigest(),all_raw_sha256=hashes);a.summary_output.write_text(s);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(windows=result['windows'],verdict=result['verdict'],background=result['background_passed'],replicated_differences=sum(p['replicated'] for p in result['comparisons']))))
if __name__=='__main__':main()
