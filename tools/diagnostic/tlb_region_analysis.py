#!/usr/bin/env python3
"""Common-victim four-region candidate discrimination; no hardware ways certification.

Protocol: docs/design/2026-10-11-tlb-cross-region.md. Actual producer geometry,
complete coverage and excitation gates precede any conditional candidate preference.
"""
import argparse,hashlib,itertools,json,statistics as st,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
from tools.diagnostic.tlb_competition_analysis import sample_check
MODE='tlb-cross-region';PROTOCOL='docs/design/2026-10-11-tlb-cross-region.md'
BUILD='docs/reviews/evidence/2026-10-11-tlb-cross-region/build.json';PLAN='docs/reviews/evidence/2026-10-11-tlb-cross-region/plan.json'
DRIVER='tools/diagnostic/run_sm8650_region.py';CONSUMER='tools/diagnostic/tlb_region_analysis.py';TARGETS=(7,100)
META=('cell','position','target','group','w','victim','history_direction','direction','passes')
def config(reverse):
 return dict(type='config',version=1,probe=MODE,targets=list(TARGETS),groups=[0,1,2],seed=137,max_w=12,offset_rotate=True,link_slots=5,f=128,history=12,w_grid=[1,8,9,12],history_directions=[0],passes=8,rounds=16,reverse=reverse,cells=48,windows=6912,region_bytes=268435456,pool_pages=524288)
def plan(reverse):
 _require(type(reverse) is bool,'region reverse type');cells=list(itertools.product(TARGETS,range(3),(0,1),(1,8,9,12)))
 if reverse:cells.reverse()
 return [config(reverse)]+[dict(type='cell',cell=f't{t}-g{g}-w{w}-d{d}',position=i,target=t,group=g,w=w,victim=0,history_direction=0,direction=d,passes=8,rounds=16) for i,(t,g,d,w) in enumerate(cells)]
def validate_plan(value):_require(_same(value,dict(forward=plan(False),reverse=plan(True))),'region actual plan mismatch')
def indices(va):
 p=va>>12;lo=p&255;mid=(p>>8)&255;hi=(p>>16)&255;return (lo,lo^mid,lo^hi,lo^mid^hi)
def relative_pages(t,g):
 return [(65536*(i%4)+4096*(i//4) if g else 4096*i)+(t^(i%4) if g==2 else t) for i in range(12)]
def proxy(hi0):
 _require(type(hi0) is int and 0<=hi0<=252 and hi0%4==0,'region aligned hi0');families=[];a=(1<<40)+(hi0<<28)
 for t,g in itertools.product(TARGETS,range(3)):
  vp=relative_pages(t,g);sets=[[indices(a+4096*p)[h] for p in vp] for h in range(4)]
  families.append(dict(target=t,group=g,relative_vpn=vp,region_nodes=[sum((p>>16)==j for p in vp) for j in range(4)],candidate_indices=sets,candidate_set_counts=[len(set(s)) for s in sets],l3_parent_relative=[p>>9 for p in vp],l3_eight_item_groups=[(p&511)//8 for p in vp]))
 return dict(hi0=hi0,families=families)
def check_geometry(g):
 """Exact requested VAs, shared victim, pure regions, candidate-safe fixed filler set."""
 _fields(g,dict(type='geometry',pool_pages=524288,filler_pool_pages=2048),'region pool shape');b=g.get('pool_base');fbase=g.get('filler_base')
 _require(type(b) is int and b>0 and b%4096==0 and b+(2<<30)<2**64,'region base')
 _require(type(fbase) is int and fbase>0 and fbase%4096==0 and fbase+2048*4096<2**64,'region filler base')
 _require(fbase+2048*4096<=b or fbase>=b+(2<<30),'region filler/pool overlap')
 a=(b+(1<<30)-1)//(1<<30)*(1<<30);_fields(g,dict(aligned_start=a),'region aligned start');ff=g.get('families');_require(type(ff) is list and len(ff)==6,'region family coverage');used=[set() for _ in range(4)]
 for f,(t,group) in zip(ff,itertools.product(TARGETS,range(3))):
  _fields(f,dict(target=t,group=group),'region family identity');want=[a+4096*p for p in relative_pages(t,group)];_require(_same(f.get('pages'),want),'region actual addresses')
  for va in want:
   for h,s in enumerate(indices(va)):used[h].add(s)
 fill=g.get('filler_pages');_require(type(fill) is list and len(fill)==512 and all(type(v) is int and v%4096==0 for v in fill) and len(set(fill))==512,'region filler identity')
 want=[]
 for i in range(2048):
  va=fbase+i*4096
  if all(s not in used[h] for h,s in enumerate(indices(va))):want.append(va)
  if len(want)==512:break
 _require(len(want)==512 and _same(sorted(fill),want),'region fixed filler set/exclusion')
 return proxy((a>>28)&255)
def audit_process(records,reverse,registered):
 validate_plan(registered);selected=registered['reverse' if reverse else 'forward'];_require(type(records) is list and len(records)==7010,'region raw coverage');_require(_same(records[0],config(reverse)),'region config mismatch');check_geometry(records[1]);cursor=2;out=[]
 for c in selected[1:]:
  for stage in ('before','after'):_fields(records[cursor],dict(type='backing',cell=c['cell'],stage=stage,base_page_bytes=4096,anon_huge_kb=0),'region backing');cursor+=1
  samples=[]
  for trial in range(16):
   for p in range(9):
    z=records[cursor];cursor+=1;_fields(z,dict(type='round',**{k:c[k] for k in META}),'region shot identity/order');sample_check(z,trial,p,8);samples.append({k:z[k] for k in ('round','role','pass_index','enabled','running','counts')})
  out.append(dict(c,samples=samples))
 return out

def analyze(run):
 _fields(run,dict(mode=MODE,processes=5),'region whole-run identity');rows=run.get('rows');_require(type(rows) is list and len(rows)==240,'region matrix coverage');geo=run.get('geometry');_require(type(geo) is list and len(geo)==5,'region geometry coverage')
 for e,g in enumerate(geo):_require(_same(g,dict(epoch=f'epoch-{e}',**proxy(g.get('hi0')))),'region derived geometry mismatch')
 cells={};i=0
 for e in range(5):
  for c in plan(bool(e%2))[1:]:
   z=rows[i];i+=1;_fields(z,dict(c,epoch=f'epoch-{e}'),'region persisted identity/order');ss=z.get('samples');_require(type(ss) is list and len(ss)==144,'region persisted shot coverage')
   for j,s in enumerate(ss):sample_check(s,j//9,j%9,8)
   cells[e,c['target'],c['group'],c['direction'],c['w']]=z
 def subset(c,role,p=None):return [s for s in c['samples'] if s['role']==role and (p is None or s['pass_index']==p)]
 lookup=[];victim=[]
 for e,t,g,d,w in itertools.product(range(5),TARGETS,range(3),(0,1),(8,9,12)):
  c=cells[e,t,g,d,w];zero=cells[e,t,g,d,1];okay=[]
  for p in range(8):
   rr,zz=subset(c,'competition',p),subset(zero,'competition',p);diff=[st.mean(r['counts'][j] for r in rr)-st.mean(r['counts'][j] for r in zz) for j in range(6)];gates=[dict(event=hex(ev),value=diff[j],lower=.75*(w-1),upper=1.25*(w-1),passed=.75*(w-1)<=diff[j]<=1.25*(w-1)) for j,ev in ((1,5),(3,47))];passed=all(x['passed'] for x in gates);okay.append(passed);lookup.append(dict(epoch=e,target=t,group=g,direction=d,w=w,pass_index=p,count_mean_differences=diff,gates=gates,observable=passed))
  rr=subset(c,'victim');zz=subset(zero,'victim');walk=[r['counts'][4] for r in rr];issues=[]
  if not all(okay):issues.append('lookup-not-observable')
  if any(r['counts'][4] for r in zero['samples']):issues.append('control-background')
  if any(x>1 for x in walk):issues.append('single-load-residual')
  rate=st.mean(x>0 for x in walk);victim.append(dict(epoch=e,target=t,group=g,direction=d,w=w,walk=walk,counts=[r['counts'] for r in rr],control_counts=[r['counts'] for r in zz],response_rate=rate,issues=issues,status='INCOMPUTABLE' if issues else 'response' if rate>=.5 else 'no-response'))
 decisions=[]
 for t in TARGETS:
  pp=[p for p in victim if p['target']==t and p['w']==12];by={g:[p for p in pp if p['group']==g] for g in range(3)};status='heterogeneous'
  if any(p['issues'] for p in pp) or not all(p['status']=='response' for p in by[0]):status='INCOMPUTABLE'
  else:
   signatures=[{p['status'] for p in by[g]} for g in (1,2)]
   if signatures==[{'response'},{'no-response'}]:status='low-only-candidate-favored'
   elif signatures==[{'no-response'},{'response'}]:status='high-fold-candidate-favored'
   elif signatures[0]==signatures[1] and len(signatures[0])==1:status='non-discriminating'
  decisions.append(dict(target=t,status=status,required_curves_per_group=10,points=pp))
 states={d['status'] for d in decisions};verdict='replicated-'+next(iter(states)) if len(states)==1 and next(iter(states)) in ('low-only-candidate-favored','high-fold-candidate-favored') else 'INCOMPUTABLE' if 'INCOMPUTABLE' in states else 'non-discriminating' if states=={'non-discriminating'} else 'heterogeneous'
 return dict(mode=MODE,windows=34560,lookup_points=lookup,victim_points=victim,decisions=decisions,verdict=verdict,all_lookup_observable=all(p['observable'] for p in lookup),physical_ways_certified=False,naming_limit='common-victim conditional low-only versus high-folded candidate preference; unknown hash/descriptor/PFN/replacement remain')

def conditions():return [dict(name=f'epoch-{e}',args=['--run',*(['--reverse'] if e%2 else [])]) for e in range(5)]

def audit_raw(path):
 """Exact inventory, committed launch/binary/plan, environment and real records."""
 expected={'manifest.json','driver.py','consumer.py','environment-policy.json','initial-environment.json','final-environment.json'}|{f'epoch-{e}'+s for e in range(5) for s in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')};_require({p.name for p in path.iterdir()}==expected and all(p.is_file() for p in path.iterdir()),'region raw inventory')
 m=json.loads((path/'manifest.json').read_text());_fields(m,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,build_evidence_path=BUILD,protocol_path=PROTOCOL,plan_path=PLAN,consumer_path=CONSUMER),'region manifest identity');_require(_same(m.get('conditions'),conditions()) and type(m.get('results')) is list and len(m['results'])==5,'region requested coverage')
 blob=lambda ref,p:subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT);sha=lambda b:hashlib.sha256(b).hexdigest();head=m['source_head']
 for file,key in ((DRIVER,'driver_sha256'),(CONSUMER,'consumer_sha256'),(PROTOCOL,'protocol_sha256'),(BUILD,'build_evidence_sha256'),(PLAN,'plan_sha256')):_require(sha(blob(head,file))==m[key],'region launch SHA '+file)
 _require(sha((path/'driver.py').read_bytes())==m['driver_sha256'],'region saved driver');_require(sha((path/'consumer.py').read_bytes())==m['consumer_sha256'],'region saved consumer');build=json.loads(blob(head,BUILD));registered=json.loads(blob(head,PLAN));validate_plan(registered)
 _require(build['binaries']['tlb_cross_region']==m['binary_sha256'] and build['source_commit']==m['binary_source_head'] and build['plan_sha256']==m['plan_sha256'],'region binary/source/plan binding')
 for p,digest in build['source_sha256'].items():_require(sha(blob(head,p))==digest and sha(blob(m['binary_source_head'],p))==digest,'region dependency SHA '+p)
 from tools.diagnostic.analyze_long_load import audit_environment
 profile=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'));policy=profile['environment_profiles']['charging-thermal']['measurement_environment'];policy['preconditions']['cpufreq_governor']='walt';env={p.name:json.loads(p.read_text()) for p in path.glob('*-environment.json')};audit_environment(env,json.loads((path/'environment-policy.json').read_text()),policy)
 rows=[];region=[]
 for e,(r,c) in enumerate(zip(m['results'],conditions())):
  _fields(r,dict(name=c['name'],exit_code=0,timed_out=False),'region result order/status');f=path/(c['name']+'.stdout.jsonl');_require(sha(f.read_bytes())==r['stdout_sha256'] and (path/(c['name']+'.stderr.log')).read_bytes()==b'','region stdout/stderr binding');records=[json.loads(l) for l in f.read_text().splitlines()];rows.extend(dict(row,epoch=c['name']) for row in audit_process(records,bool(e%2),registered));region.append(dict(epoch=c['name'],**check_geometry(records[1])))
 result=dict(mode=MODE,processes=5,source_branch=m['source_branch'],source_head=head,binary_source_head=m['binary_source_head'],binary_sha256=m['binary_sha256'],raw_directory=path.name,manifest_sha256=sha((path/'manifest.json').read_bytes()),max_cpu_c_range=[min(v['snapshot']['thermal']['max_cpu_c'] for v in env.values()),max(v['snapshot']['thermal']['max_cpu_c'] for v in env.values())],geometry=region,rows=rows)
 return result,{p.name:sha(p.read_bytes()) for p in sorted(path.iterdir())}
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--summary-output',type=Path,required=True);a=p.parse_args(argv);run,hashes=audit_raw(a.raw);result=analyze(run);s=json.dumps(run,indent=2,allow_nan=False)+'\n';result.update(data_origin='device-raw',input_sha256=hashlib.sha256(s.encode()).hexdigest(),all_raw_sha256=hashes);a.summary_output.write_text(s);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(windows=result['windows'],lookup_passed=sum(p['observable'] for p in result['lookup_points']),lookup_points=len(result['lookup_points']),verdict=result['verdict'],decisions=[{k:d[k] for k in ('target','status')} for d in result['decisions']])))
if __name__=='__main__':main()
