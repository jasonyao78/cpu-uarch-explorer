#!/usr/bin/env python3
"""同VA集合/PFN关联的严格原始证书与有限统计；不认证HPA或物理entries。

契约：docs/design/2026-10-12-tlb-pfn-association.md。先审真实图/页面/π，
再算匿名统计；显式保留虚拟顺序残余、自然激励不足及删失。
"""
import argparse,hashlib,json,statistics as st,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
from tools.diagnostic.tlb_alias_analysis import permutation,check_wire
MODE='tlb-pfn-association';PROTOCOL='docs/design/2026-10-12-tlb-pfn-association.md';BUILD='docs/reviews/evidence/2026-10-12-tlb-pfn-association/build.json';PLAN='docs/reviews/evidence/2026-10-12-tlb-pfn-association/plan.json';DRIVER='tools/diagnostic/run_sm8650_tlb_association.py';CONSUMER='tools/diagnostic/tlb_association_analysis.py'
GRID=(1024,1280,1536,1792,2048,2304,2560,3072);ASSIGNMENTS=('natural','no-adjacent');ORDERS=('random','reverse-random');MASK=0x9e3779b97f4a7c15

def config(reverse):
 """固定目标配置；软件plan与目标stdout必须逐类型相同。"""
 return dict(type='config',version=1,probe=MODE,backing_pages=4096,pool_pages=4096,alignment_bytes=2097152,order_seed=137,n_grid=list(GRID),load_budget=1048576,rounds=3,events=[17,8,5,52,33108,33109],pmu_type=8,reverse=reverse,cells=33,windows=99,decode_loop_instructions=4)
def plan(reverse):
 """返回唯一完整cell顺序；反序不改变物理访问order的定义。"""
 _require(type(reverse) is bool,'association reverse type');cc=[dict(type='cell',cell='floor',position=0,assignment='none',order='empty',n=0,loads=0,span_bytes=0,line_bytes=0,rounds=3,mask=0)]
 for a in ASSIGNMENTS:
  for o in ORDERS:
   for n in GRID:cc.append(dict(type='cell',cell=f'{a}-{o}-n{n}',position=0,assignment=a,order=o,n=n,loads=1048576//n*n,span_bytes=n*4096,line_bytes=n*64,rounds=3,mask=MASK))
 if reverse:cc.reverse()
 return [config(reverse),*[dict(c,position=i) for i,c in enumerate(cc)]]
def validate_plan(p):
 """拒绝任何不同于真实注册producer矩阵的计划。"""
 _require(_same(p,dict(forward=plan(False),reverse=plan(True))),'association actual plan')
def weave(pfns):
 """独立整数布局oracle；只用于核验C++，不作为实际PFN观测。"""
 n=len(pfns);_require(n>=1024 and n<=4096 and n%64==0 and all(type(p) is int and 0<p<2**55 for p in pfns) and len(set(pfns))==n,'association oracle PFNs');out=list(range(n));bad=lambda i:abs(pfns[out[i+1]]-pfns[out[i]])==1
 for a in range(n-1):
  if not bad(a):continue
  b=a+1;fixed=False
  for c in range(b%64,n,64):
   if c==b:continue
   out[b],out[c]=out[c],out[b]
   if all(not bad(e) for e in {b-1,b,c-1,c} if 0<=e<n-1):fixed=True;break
   out[b],out[c]=out[c],out[b]
  _require(fixed,'association oracle no candidate')
 _require(sorted(out)==list(range(n)) and all(j%64==i%64 for j,i in enumerate(out)) and not any(bad(i) for i in range(n-1)),'association oracle certificate');return out

def geometry(c,base,pfns):
 """由canonical原始PFN复验位置图；绝不由意图标签认定零邻接。"""
 n=c['n'];pp=weave(pfns[:n]) if c['assignment']=='no-adjacent' else list(range(n));inv=[0]*n;hist=[0]*256;parents=set()
 for j,i in enumerate(pp):inv[i]=j;hist[(base//4096+j)%256]+=1;parents.add((base//4096+j)>>9)
 oo=list(permutation(n,137)) if n else []
 if c['order']=='reverse-random':oo.reverse()
 return dict(type='geometry',cell=c['cell'],position_nodes=pp,node_positions=inv,order_indices=oo,offsets=[64*(i%64) for i in range(n)],vpn_low8_hist=hist,l3_parent_count=len(parents),l3_parent_ids=sorted(parents))
def graph(c,g,base):
 """独立解码同物理节点闭环；stored_words必须来自实际内存证书。"""
 n=c['n'];words=[0]*n;o=g['order_indices'];node=lambda i:base+4096*g['node_positions'][i]+64*(i%64)
 for j,i in enumerate(o):words[i]=node(o[(j+1)%n])^c['mask']
 return dict(cell=c['cell'],head=node(o[0]) if o else 0,stored_words=words)
def sample_check(s,c,t):
 """同窗raw u64/IR/noMUX验证；typed bool不能冒充int。"""
 _fields(s,dict(type='round',cell=c['cell'],position=c['position'],round=t,head_returned=True),'association sample identity');_require(type(s.get('enabled')) is int and 0<s['enabled']<2**64 and type(s.get('running')) is int and s['running']==s['enabled'],'association mux/time');v=s.get('counts');_require(type(v) is list and len(v)==6 and all(type(x) is int and 0<=x<2**64 for x in v),'association counts')
 if c['n']:_require(v[0]>0 and abs(v[1]-4*c['loads'])<=max(1000,.01*4*c['loads']),'association IR')
def audit_process(records,reverse,registered):
 """完整366条真实JSONL→匿名行；canonical与alias前后PFN同时验证。"""
 validate_plan(registered);_require(type(records) is list and len(records)==366,'association raw coverage');_require(_same(records[0],config(reverse)),'association config');pmu=records[1];ids=pmu.get('ids');_fields(pmu,dict(type='pmu'),'association PMU');_require(type(ids) is list and len(ids)==6 and all(type(i) is int and 0<i<2**64 for i in ids) and len(set(ids))==6,'association IDs');back=records[2];_fields(back,dict(type='physical-backing',backing_pages=4096,pool_pages=4096,pte_cont_state='UNKNOWN'),'association backing');base=back.get('arena_base');cb=back.get('canonical_base');_require(type(base) is int and 0<base<=2**64-4096*4096 and base%2097152==0 and type(cb) is int and 0<cb<=2**64-4096*4096 and cb%4096==0 and (cb+4096*4096<=base or base+4096*4096<=cb),'association owned base');cp=back.get('canonical_pfns');_require(type(cp) is list and len(cp)==4096 and all(type(p) is int and 0<p<2**55 for p in cp) and len(set(cp))==4096,'association canonical PFNs');check_wire(back.get('canonical_entries'),cp);cursor=3;out=[]
 for c in plan(reverse)[1:]:
  _require(_same(records[cursor],c),'association cell');cursor+=1;g=geometry(c,base,cp);_require(_same(records[cursor],g),'association mapping geometry');cursor+=1
  for stage in ('before','after'):
   _fields(records[cursor],dict(type='backing',cell=c['cell'],stage=stage,kernel_page_kb=4,mmu_page_kb=4,anon_huge_kb=0,shmem_pmd_kb=0,file_pmd_kb=0),'association actual pages');cursor+=1;cert=records[cursor]
   for tag in ('alias','canonical'):check_wire(cert.get(tag+'_entries'),cp[:c['n']])
   _require(_same(cert,dict(type='pfn-certificate',cell=c['cell'],stage=stage,alias_pfns=cp[:c['n']],alias_entries=cert['alias_entries'],canonical_pfns=cp[:c['n']],canonical_entries=cert['canonical_entries'])),'association PFN conflict');cursor+=1
   _require(_same(records[cursor],dict(graph(c,g,base),type='graph-certificate',stage=stage)),'association actual stored graph');cursor+=1
  pp=g['position_nodes'];adj=sum(abs(cp[pp[i+1]]-cp[pp[i]])==1 for i in range(c['n']-1));ascending=sum(cp[pp[i+1]]==cp[pp[i]]+1 for i in range(c['n']-1));_require(c['assignment']!='no-adjacent' or adj==0,'association actual no adjacency');samples=[]
  for t in range(3):ss=records[cursor];cursor+=1;sample_check(ss,c,t);samples.append(ss)
  relative=dict(g,l3_parent_ids=[p-(base//4096>>9) for p in g['l3_parent_ids']]);out.append(dict(c,geometry=relative,pmu_ids=ids,samples=samples,physical_nodes_verified=c['n'],stored_graph_verified=c['n'],neighbor_pfn_pairs=adj,ascending_pfn_pairs=ascending,no_adjacent_verified=c['assignment']=='no-adjacent'))
 return out

def ratio(v,loads):
 """保持原始比例，带符号背景修正只作为独立辅助列。"""
 return dict(cycles_per_load=v[0]/loads,l1_refills_per_load=v[2]/loads,walks_per_load=v[3]/loads,l1_hw_prefetch_per_load=v[4]/loads,l2_hw_prefetch_per_load=v[5]/loads)
def analyze(run):
 """完整六配对差与逐曲线reach；命名判据不换算物理entry。"""
 _fields(run,dict(mode=MODE,processes=3),'association matrix');rows=run.get('rows');_require(type(rows) is list and len(rows)==99,'association rows');cursor=0;by={}
 for e in range(3):
  for c in plan(bool(e%2))[1:]:
   r=rows[cursor];cursor+=1;_fields(r,dict(c,epoch=f'epoch-{e}',physical_nodes_verified=c['n'],stored_graph_verified=c['n'],no_adjacent_verified=c['assignment']=='no-adjacent'),'association row identity')
   for key in ('neighbor_pfn_pairs','ascending_pfn_pairs'):_require(type(r.get(key)) is int and 0<=r[key]<=max(0,c['n']-1),'association adjacency summary')
   _require(r['ascending_pfn_pairs']<=r['neighbor_pfn_pairs'] and (c['assignment']!='no-adjacent' or r['neighbor_pfn_pairs']==0),'association zero adjacency summary');_require(type(r.get('samples')) is list and len(r['samples'])==3,'association sample coverage')
   for t,s in enumerate(r['samples']):sample_check(s,c,t)
   by[e,c['cell']]=r
 points=[];checks=[];tapchecks=[];windows=[];lookup={};point_pass={}
 for e in range(3):
  bg=[st.median(s['counts'][j] for s in by[e,'floor']['samples']) for j in range(6)]
  for c in plan(bool(e%2))[1:]:
   if not c['n']:continue
   r=by[e,c['cell']];ss=r['samples'];sums=[sum(s['counts'][j] for s in ss) for j in range(6)];p=dict(epoch=e,**c,**ratio(sums,3*c['loads']),neighbor_pfn_pairs=r['neighbor_pfn_pairs'],ascending_pfn_pairs=r['ascending_pfn_pairs']);points.append(p);key=e,c['assignment'],c['order'],c['n'];lookup[key]=p;point_pass[key]=True
   for s in ss:
    v=s['counts'];gates=dict(cycle_background=bg[0]<=.01*v[0],translation_background=all(bg[j]<=.001*c['loads'] for j in (2,3)),l1_translation_pressure=.75*c['loads']<=v[2]<=1.25*c['loads']);ok=all(gates.values());point_pass[key]&=ok;checks.append(dict(epoch=e,cell=c['cell'],round=s['round'],gates=gates,passed=ok));tapchecks.append(dict(epoch=e,cell=c['cell'],round=s['round'],passed=all(bg[j]<=.001*c['loads'] for j in (4,5))));windows.append(dict(epoch=e,cell=c['cell'],round=s['round'],counts=v,ratios=ratio(v,c['loads']),corrected_ratios=ratio([v[j]-bg[j] for j in range(6)],c['loads'])))
 bgok=all(x['passed'] for x in checks);comparisons=[]
 for n in GRID:
  d=[dict(epoch=e,order=o,delta=lookup[e,'no-adjacent',o,n]['walks_per_load']-lookup[e,'natural',o,n]['walks_per_load']) for e in range(3) for o in ORDERS];vv=[x['delta'] for x in d];rep=all(v>=.10 for v in vv) or all(v<=-.10 for v in vv);comparisons.append(dict(n=n,deltas=d,range=[min(vv),max(vv)],numeric_replicated=rep,replicated=bgok and rep))
 excited=sorted(n for n in GRID if n>=1792 and all(lookup[e,'natural',o,n]['ascending_pfn_pairs']/(n-1)>=.10 for e in range(3) for o in ORDERS));verdict='INCOMPUTABLE' if not bgok else 'ASSOCIATION_SENSITIVE' if any(c['replicated'] for c in comparisons) else 'ASSOCIATION_NOT_CHANGED_AT_DETECTION_SCALE' if all(abs(v['delta'])<.10 for c in comparisons for v in c['deltas']) else 'INCONCLUSIVE';curves=[]
 for assignment in ASSIGNMENTS:
  for e in range(3):
   for order in ORDERS:
    values=[lookup[e,assignment,order,n]['walks_per_load'] for n in GRID];states=['below' if x<=.05 else 'above' if x>=.20 else 'ambiguous' for x in values];interval=None
    if not all(point_pass[e,assignment,order,n] for n in GRID):status='INCOMPUTABLE'
    elif any(states[i]=='above' and 'below' in states[i+1:] for i in range(len(states))):status='nonmonotonic'
    elif 'ambiguous' in states:status='ambiguous'
    elif 'above' not in states:status='right-censored'
    elif states[0]=='above':status='left-censored'
    else:
     i=states.index('above')
     if i==len(states)-1:status='right-censored'
     else:status='interval';interval=[GRID[i-1],GRID[i]]
    curves.append(dict(assignment=assignment,epoch=e,order=order,walks_per_load=values,states=states,status=status,interval=interval))
 reach=[]
 for assignment in ASSIGNMENTS:
  cc=[c for c in curves if c['assignment']==assignment];rep=all(c['status']=='interval' and c['interval']==cc[0]['interval'] for c in cc);reach.append(dict(assignment=assignment,status='INTERVAL_REPLICATED' if rep else 'heterogeneous',interval=cc[0]['interval'] if rep else None))
 observed=any(w['counts'][j] for w in windows for j in (4,5));tapok=all(x['passed'] for x in tapchecks)
 return dict(mode=MODE,windows=297,verdict=verdict,background_passed=bgok,comparisons=comparisons,contiguity_control='CONTIGUITY_CONTROL_EXCITED' if len(excited)>=2 else 'NOT_EXCITED',excited_n=excited,epoch_points=points,window_ratios=windows,background_checks=checks,prefetch_background_checks=tapchecks,prefetch_status='INCOMPUTABLE' if not tapok else 'PREFETCH_COUNTS_OBSERVED' if observed else 'NO_PREFETCH_COUNTS_IN_MATRIX',curves=curves,reach=reach,physical_entries_certified=False,hpa_attributed=False,pte_cont_state='UNKNOWN',naming_limit='same VA lines and physical demand trace; virtual visit order changes, no unique HPA/descriptor/replacement attribution')

def conditions():return [dict(name=f'epoch-{e}',args=['--run',*(['--reverse'] if e%2 else [])]) for e in range(3)]

def audit_raw(path):
 """Exact inventory, committed launch/binary/plan, environment and real records."""
 expected={'manifest.json','driver.py','consumer.py','environment-policy.json','initial-environment.json','final-environment.json'}|{f'epoch-{e}'+s for e in range(3) for s in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')};_require({p.name for p in path.iterdir()}==expected and all(p.is_file() for p in path.iterdir()),'reach raw inventory')
 m=json.loads((path/'manifest.json').read_text());_fields(m,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,build_evidence_path=BUILD,protocol_path=PROTOCOL,plan_path=PLAN,consumer_path=CONSUMER),'reach manifest identity');_require(_same(m.get('conditions'),conditions()) and type(m.get('results')) is list and len(m['results'])==3,'reach requested coverage')
 blob=lambda ref,p:subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT);sha=lambda b:hashlib.sha256(b).hexdigest();head=m['source_head']
 for file,key in ((DRIVER,'driver_sha256'),(CONSUMER,'consumer_sha256'),(PROTOCOL,'protocol_sha256'),(BUILD,'build_evidence_sha256'),(PLAN,'plan_sha256')):_require(sha(blob(head,file))==m[key],'reach launch SHA '+file)
 _require(sha((path/'driver.py').read_bytes())==m['driver_sha256'],'reach saved driver');_require(sha((path/'consumer.py').read_bytes())==m['consumer_sha256'],'reach saved consumer');build=json.loads(blob(head,BUILD));registered=json.loads(blob(head,PLAN));validate_plan(registered)
 _require(build['binaries']['tlb_pfn_association']==m['binary_sha256'] and build['source_commit']==m['binary_source_head'] and build['plan_sha256']==m['plan_sha256'],'reach binary/source/plan binding')
 for p,digest in build['source_sha256'].items():_require(sha(blob(head,p))==digest and sha(blob(m['binary_source_head'],p))==digest,'reach dependency SHA '+p)
 from tools.diagnostic.analyze_long_load import audit_environment
 profile=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'));policy=profile['environment_profiles']['charging-thermal']['measurement_environment'];policy['preconditions']['cpufreq_governor']='walt';env={p.name:json.loads(p.read_text()) for p in path.glob('*-environment.json')};audit_environment(env,json.loads((path/'environment-policy.json').read_text()),policy)
 rows=[];mapping=[]
 for e,(r,c) in enumerate(zip(m['results'],conditions())):
  _fields(r,dict(name=c['name'],exit_code=0,timed_out=False),'reach result order/status');f=path/(c['name']+'.stdout.jsonl');_require(sha(f.read_bytes())==r['stdout_sha256'] and (path/(c['name']+'.stderr.log')).read_bytes()==b'','reach stdout/stderr binding');records=[json.loads(l) for l in f.read_text().splitlines()];rows.extend(dict(row,epoch=c['name']) for row in audit_process(records,bool(e%2),registered));mapping.append(dict(epoch=e,physical_backing_pages=4096,aliases=1,canonical_nonzero_unique=True,absolute_addresses_public=False))
 result=dict(mode=MODE,processes=3,source_branch=m['source_branch'],source_head=head,binary_source_head=m['binary_source_head'],binary_sha256=m['binary_sha256'],raw_directory=path.name,manifest_sha256=sha((path/'manifest.json').read_bytes()),max_cpu_c_range=[min(v['snapshot']['thermal']['max_cpu_c'] for v in env.values()),max(v['snapshot']['thermal']['max_cpu_c'] for v in env.values())],mapping=mapping,rows=rows)
 return result,{p.name:sha(p.read_bytes()) for p in sorted(path.iterdir())}
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--summary-output',type=Path,required=True);a=p.parse_args(argv);run,hashes=audit_raw(a.raw);result=analyze(run);s=json.dumps(run,indent=2,allow_nan=False)+'\n';result.update(data_origin='device-raw',input_sha256=hashlib.sha256(s.encode()).hexdigest(),all_raw_sha256=hashes);a.summary_output.write_text(s);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(windows=result['windows'],verdict=result['verdict'],background=result['background_passed'],replicated_differences=sum(p['replicated'] for p in result['comparisons']))))
if __name__=='__main__':main()
