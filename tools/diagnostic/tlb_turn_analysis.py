#!/usr/bin/env python3
"""Paired target/high-VPN geometry; raw acceptance before finite response naming.

Contract: docs/design/2026-10-11-tlb-local-turn.md. A collection signature
and VA descriptor-range proxy are not certified hardware hash/physical ways.
"""
import argparse,hashlib,itertools,json,statistics as st,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
from tools.diagnostic.tlb_competition_analysis import sample_check
MODE='tlb-local-turn';PROTOCOL='docs/design/2026-10-11-tlb-local-turn.md'
BUILD='docs/reviews/evidence/2026-10-11-tlb-local-turn/build.json';PLAN='docs/reviews/evidence/2026-10-11-tlb-local-turn/plan.json'
DRIVER='tools/diagnostic/run_sm8650_turn.py';TARGETS=(7,100);STEPS=(1,16)
META=('cell','position','target','step','h','w','victim','history_direction','direction','passes')
def config(reverse):
 return dict(type='config',version=1,probe=MODE,targets=list(TARGETS),steps=list(STEPS),seed=137,max_w=12,offset_rotate=True,link_slots=5,f=128,history=12,w_grid=[1,6,7,8,9,10],history_directions=[0],passes=8,rounds=16,reverse=reverse,cells=96,windows=13824)
def plan(reverse):
 """Independent frozen finite cells; all identities survive to public results."""
 _require(type(reverse) is bool,'geometry reverse type');cells=list(itertools.product(TARGETS,STEPS,(0,1),(1,2),(1,6,7,8,9,10)))
 if reverse:cells.reverse()
 return [config(reverse)]+[dict(type='cell',cell=f't{t}-s{s}-h{h}-w{w}-d{d}',position=i,target=t,step=s,h=h,w=w,victim=0 if w==1 else 4,history_direction=0,direction=d,passes=8,rounds=16) for i,(t,s,d,h,w) in enumerate(cells)]
def validate_plan(value):_require(_same(value,dict(forward=plan(False),reverse=plan(True))),'geometry actual plan mismatch')
def check_geometry(g):
 """Arithmetic expectation from pool base, with alternate-model dispersion."""
 _fields(g,dict(type='geometry',pool_pages=65536),'geometry pool shape');base=g.get('pool_base');_require(type(base) is int and base>0 and base%4096==0,'geometry base type/alignment')
 families=g.get('families');_require(type(families) is list and len(families)==8,'geometry family coverage');q0=((base>>12)+255)//256;used=[set(),set()];proxies=[]
 def index(h,v):p=v>>12;return (p if h==1 else p^(p>>8))&255
 for f,(t,s,h) in zip(families,itertools.product(TARGETS,STEPS,(1,2))):
  _fields(f,dict(target=t,step=s,h=h),'geometry family identity/order/type');want=[(((q0+i*s)<<8)|(t if h==1 else t^((q0+i*s)&255)))<<12 for i in range(12)];_require(_same(f.get('pages'),want) and all(base<=v<base+65536*4096 for v in want),'geometry actual addresses do not match request')
  _require(len({index(3-h,v) for v in want})==12,'geometry alternate signature not dispersed')
  for m in (1,2):used[m-1].update(index(m,v) for v in want)
  proxies.append(dict(target=t,step=s,h=h,span_bytes=want[-1]-want[0],vpn_region_keys=[(v>>12)>>9 for v in want],vpn_local_keys=[(v>>12)&511 for v in want],unique_regions_by_w={str(w):len({v>>21 for v in want[:w]}) for w in (6,7,8,9,10)}))
 fill=g.get('filler_pages');_require(type(fill) is list and len(fill)==512 and all(type(v) is int and v>0 and v%4096==0 for v in fill) and len(set(fill))==512,'geometry filler identity/type')
 _require(all(index(m,v) not in used[m-1] for v in fill for m in (1,2)),'geometry filler candidate overlap')
 return proxies

def audit_process(records,reverse,registered):
 """Real config/geometry/backing and every shot; zero implicit defaults."""
 validate_plan(registered);selected=registered['reverse' if reverse else 'forward'];_require(type(records) is list and len(records)==14018,'geometry raw record coverage');_require(_same(records[0],config(reverse)),'geometry config mismatch');check_geometry(records[1]);cursor=2;out=[]
 for c in selected[1:]:
  for stage in ('before','after'):_fields(records[cursor],dict(type='backing',cell=c['cell'],stage=stage,base_page_bytes=4096,anon_huge_kb=0),'geometry backing endpoint');cursor+=1
  samples=[]
  for t in range(16):
   for p in range(9):
    r=records[cursor];cursor+=1;_fields(r,dict(type='round',**{k:c[k] for k in META}),'geometry shot metadata/order/type');sample_check(r,t,p,8);samples.append({k:r[k] for k in ('round','role','pass_index','enabled','running','counts')})
  out.append(dict(c,samples=samples))
 return out

def analyze(run):
 """All five mappings and every geometry before matching controls and naming."""
 _fields(run,dict(mode=MODE,processes=5),'geometry run identity');rows=run.get('rows');_require(type(rows) is list and len(rows)==480,'geometry whole matrix');cells={};i=0
 for e in range(5):
  for c in plan(bool(e%2))[1:]:
   r=rows[i];i+=1;_fields(r,dict(c,epoch=f'epoch-{e}'),'geometry public identity/order/type');samples=r.get('samples');_require(type(samples) is list and len(samples)==144,'geometry complete shots')
   for j,s in enumerate(samples):sample_check(s,j//9,j%9,8)
   cells[e,c['target'],c['step'],c['direction'],c['h'],c['w']]=r
 def subset(c,role,p=None):return [s for s in c['samples'] if s['role']==role and (p is None or s['pass_index']==p)]
 lookup=[];victim=[]
 for e,t,s,d,h,w in itertools.product(range(5),TARGETS,STEPS,(0,1),(1,2),(6,7,8,9,10)):
  c=cells[e,t,s,d,h,w];zero=cells[e,t,s,d,h,1];okay=[]
  for p in range(8):
   rr,zz=subset(c,'competition',p),subset(zero,'competition',p);diff=[st.mean(r['counts'][j] for r in rr)-st.mean(r['counts'][j] for r in zz) for j in range(6)];gates=[dict(event=hex(ev),value=diff[j],lower=.75*(w-1),upper=1.25*(w-1),passed=.75*(w-1)<=diff[j]<=1.25*(w-1)) for j,ev in ((1,5),(3,47))];passed=all(g['passed'] for g in gates);okay.append(passed);lookup.append(dict(epoch=e,target=t,step=s,direction=d,h=h,w=w,pass_index=p,count_mean_differences=diff,gates=gates,observable=passed))
  rr=subset(c,'victim');zz=subset(zero,'victim');walk=[r['counts'][4] for r in rr];issues=[]
  if not all(okay):issues.append('lookup-not-observable')
  if any(r['counts'][4] for r in zz):issues.append('control-background')
  if any(x>1 for x in walk):issues.append('single-load-residual')
  rate=st.mean(x>0 for x in walk);victim.append(dict(epoch=e,target=t,step=s,direction=d,h=h,w=w,walk=walk,counts=[r['counts'] for r in rr],control_counts=[r['counts'] for r in zz],response_rate=rate,issues=issues,status='INCOMPUTABLE' if issues else 'response' if rate>=.5 else 'no-response',response_observed=not issues and rate>=.5))
 replication=[]
 for t,s,h,w in itertools.product(TARGETS,STEPS,(1,2),(6,7,8,9,10)):
  related=[p for p in victim if (p['target'],p['step'],p['h'],p['w'])==(t,s,h,w)];epochs=[e for e in range(5) if all(p['response_observed'] for p in related if p['epoch']==e)];replication.append(dict(target=t,step=s,h=h,w=w,epochs=epochs,required_epochs=5,passed=len(epochs)==5))
 curves=[]
 for e,t,step,h,d in itertools.product(range(5),TARGETS,STEPS,(1,2),(0,1)):
  points=[next(p for p in victim if (p['epoch'],p['target'],p['step'],p['h'],p['direction'],p['w'])==(e,t,step,h,d,w)) for w in (6,7,8,9,10)]
  status='ambiguous';interval=None
  if any(p['issues'] for p in points):status='INCOMPUTABLE'
  elif not any(p['response_observed'] for p in points):status='no-onset-through10'
  elif any(points[i]['response_observed'] and not points[j]['response_observed'] for i in range(5) for j in range(i+1,5)):status='ambiguous'
  elif points[0]['response_observed']:status='left-censored'
  else:
   i=next(i for i,p in enumerate(points) if p['response_observed'])
   if all(p['response_observed'] for p in points[i:]):
    if i==4:status='right-censored'
    else:status='interval';interval=[points[i-1]['w'],points[i]['w']]
  curves.append(dict(epoch=e,target=t,step=step,h=h,direction=d,status=status,interval=interval,points=[dict(w=p['w'],response_rate=p['response_rate'],issues=p['issues']) for p in points]))
 onsets=[]
 for t,step,h in itertools.product(TARGETS,STEPS,(1,2)):
  pp=[p for p in curves if (p['target'],p['step'],p['h'])==(t,step,h)];states={(p['status'],tuple(p['interval'] or [])) for p in pp};status='ambiguous';interval=None
  if any(p['status']=='INCOMPUTABLE' for p in pp):status='INCOMPUTABLE'
  elif len(states)==1:
   status,ii=next(iter(states));interval=list(ii) or None
   if status=='interval':status='replicated-operational-interval'
  onsets.append(dict(target=t,step=step,h=h,status=status,interval=interval,required_curves=10,curves=pp))
 return dict(mode=MODE,processes=5,windows=69120,lookup_points=lookup,victim_points=victim,replication=replication,onsets=onsets,all_lookup_observable=all(p['observable'] for p in lookup),physical_ways_certified=False,naming_limit='finite paired address-family victim response interval; descriptor/hash/PFN/cache alternatives remain')


def conditions():return [dict(name=f'epoch-{e}',args=['--run',*(['--reverse'] if e%2 else [])]) for e in range(5)]
def audit_raw(path):
 """Exact inventory, committed launch/binary/plan, environment and real records."""
 expected={'manifest.json','driver.py','environment-policy.json','initial-environment.json','final-environment.json'}|{f'epoch-{e}'+s for e in range(5) for s in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')};_require({p.name for p in path.iterdir()}==expected and all(p.is_file() for p in path.iterdir()),'geometry raw inventory')
 m=json.loads((path/'manifest.json').read_text());_fields(m,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,build_evidence_path=BUILD,protocol_path=PROTOCOL,plan_path=PLAN),'geometry manifest identity');_require(_same(m.get('conditions'),conditions()) and type(m.get('results')) is list and len(m['results'])==5,'geometry requested coverage')
 blob=lambda ref,p:subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT);sha=lambda b:hashlib.sha256(b).hexdigest();head=m['source_head']
 for file,key in ((DRIVER,'driver_sha256'),(PROTOCOL,'protocol_sha256'),(BUILD,'build_evidence_sha256'),(PLAN,'plan_sha256')):_require(sha(blob(head,file))==m[key],'geometry launch SHA '+file)
 _require(sha((path/'driver.py').read_bytes())==m['driver_sha256'],'geometry saved driver');build=json.loads(blob(head,BUILD));registered=json.loads(blob(head,PLAN));validate_plan(registered)
 _require(build['binaries']['tlb_local_turn']==m['binary_sha256'] and build['source_commit']==m['binary_source_head'] and build['plan_sha256']==m['plan_sha256'],'geometry binary/source/plan binding')
 for p,digest in build['source_sha256'].items():_require(sha(blob(head,p))==digest and sha(blob(m['binary_source_head'],p))==digest,'geometry dependency SHA '+p)
 from tools.diagnostic.analyze_long_load import audit_environment
 profile=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'));policy=profile['environment_profiles']['charging-thermal']['measurement_environment'];policy['preconditions']['cpufreq_governor']='walt';env={p.name:json.loads(p.read_text()) for p in path.glob('*-environment.json')};audit_environment(env,json.loads((path/'environment-policy.json').read_text()),policy)
 rows=[];geometry=[]
 for e,(r,c) in enumerate(zip(m['results'],conditions())):
  _fields(r,dict(name=c['name'],exit_code=0,timed_out=False),'geometry result order/status');f=path/(c['name']+'.stdout.jsonl');_require(sha(f.read_bytes())==r['stdout_sha256'] and (path/(c['name']+'.stderr.log')).read_bytes()==b'','geometry stdout/stderr binding');records=[json.loads(l) for l in f.read_text().splitlines()];rows.extend(dict(row,epoch=c['name']) for row in audit_process(records,bool(e%2),registered));geometry.append(dict(epoch=c['name'],families=check_geometry(records[1])))
 result=dict(mode=MODE,processes=5,source_branch=m['source_branch'],source_head=head,binary_source_head=m['binary_source_head'],binary_sha256=m['binary_sha256'],raw_directory=path.name,manifest_sha256=sha((path/'manifest.json').read_bytes()),max_cpu_c_range=[min(v['snapshot']['thermal']['max_cpu_c'] for v in env.values()),max(v['snapshot']['thermal']['max_cpu_c'] for v in env.values())],geometry=geometry,rows=rows)
 return result,{p.name:sha(p.read_bytes()) for p in sorted(path.iterdir())}
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--summary-output',type=Path,required=True);a=p.parse_args(argv);run,hashes=audit_raw(a.raw);result=analyze(run);s=json.dumps(run,indent=2,allow_nan=False)+'\n';result.update(data_origin='device-raw',input_sha256=hashlib.sha256(s.encode()).hexdigest(),all_raw_sha256=hashes);a.summary_output.write_text(s);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(windows=result['windows'],lookup_passed=sum(p['observable'] for p in result['lookup_points']),lookup_points=len(result['lookup_points']),onsets=[{k:p[k] for k in ('target','step','h','status','interval')} for p in result['onsets']])))
if __name__=='__main__':main()
