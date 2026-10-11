#!/usr/bin/env python3
"""Fixed-program identical-reinstall control; no physical allocation inference.

Frozen purpose/gates: docs/design/2026-10-11-rob-resident-control.md. Exact
producer words, schedule, raw inventory and provenance are audited before statistics.
"""
import argparse,hashlib,json,statistics as st,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
from tools.diagnostic.rob_dependency_analysis import expected_code
MODE='rob-resident-control'
PROTOCOL='docs/design/2026-10-11-rob-resident-control.md'
BUILD='docs/reviews/evidence/2026-10-11-rob-resident-control/build.json'
PLAN='docs/reviews/evidence/2026-10-11-rob-resident-control/plan.json'
DRIVER='tools/diagnostic/run_sm8650_rob_resident.py'
CONSUMER='tools/diagnostic/rob_resident_analysis.py'
SPECS=(('none','independent',0),('none','independent',128),('none','dependent',128),('fsqrt','independent',128),('fsqrt','dependent',128))
EVENTS=(17,8,58,59,33133,35);ITERATIONS=131072

def conditions():
 return [dict(name=f'e{e}-{a}-{link}-n{n}',args=['--run','--anchor',a,'--link',link,'--n',str(n),*(['--reverse'] if e%2 else [])]) for e in range(3) for a,link,n in (SPECS if e%2==0 else tuple(reversed(SPECS)))]
def identity(c):
 args=c['args'];return args[2],args[4],int(args[6]),'--reverse' in args

def expected(a,link,n,rev):
 cfg=dict(type='config',version=1,probe=MODE,**{'class':'add'},anchor=a,link=link,n=n,chain=16,iterations=ITERATIONS,warmup_iterations=ITERATIONS,blocks=8,windows=16,reverse=rev,events=list(EVENTS),pmu_type=8,loop_mod64=0)
 data=expected_code({'args':['--anchor-link',link,'-a',a,'--chain','16','-n',str(n)]});words=list(struct.unpack('<'+'I'*(len(data)//4),data));loop=2*n+(32 if a=='fsqrt' else 0)+4
 program=dict(type='program',loop_offset=64,branch_offset=4*(16+loop-1),loop_instructions=loop,prologue_instructions=16,code_bytes=len(data),words=words)
 ss=[dict(type='schedule',block=b,slot=s,preparation=v) for b in range(8) for s,v in enumerate(('resident','reinstall') if b%2==0 else ('reinstall','resident'))]
 if rev:ss.reverse()
 generation=1
 for pos,s in enumerate(ss):
  generation+=s['preparation']=='reinstall';s.update(position=pos,installation_generation=generation)
 return [cfg,program,*ss]
def plans():return {f'{a}-{link}-{n}-{int(rev)}':expected(a,link,n,rev) for a,link,n in SPECS for rev in (False,True)}
def validate_plan(p):_require(_same(p,plans()),'resident actual registered plan mismatch')

def audit_process(rr,c,registered):
 """One real generated program, one VA, exact maintenance sequence and 16 windows."""
 validate_plan(registered);a,link,n,rev=identity(c);want=expected(a,link,n,rev)
 _require(type(rr) is list and len(rr)==19,'resident raw window coverage');_require(_same(rr[:2],want[:2]),'resident config/program mismatch')
 runtime=rr[2];_fields(runtime,dict(type='runtime',cpu=7,fpcr=0),'resident CPU/FPCR')
 base=runtime.get('code_base');ids=runtime.get('event_ids');_require(type(base) is int and base>0 and base%4096==0,'resident code base')
 _require(type(ids) is list and len(ids)==6 and all(type(x) is int and 0<x<2**64 for x in ids) and len(set(ids))==6,'resident kernel IDs')
 ir=ITERATIONS*want[1]['loop_instructions']+want[1]['prologue_instructions']+1
 for r,s in zip(rr[3:],want[2:]):
  _fields(r,dict(s,type='round',code_base=base,code_matches_plan=True),'resident sample schedule/code/generation')
  _require(all(type(r.get(k)) is int and 0<r[k]<2**64 for k in ('ns','enabled','running')) and r['enabled']==r['running'],'resident time/mux')
  counts=r.get('counts');_require(type(counts) is list and len(counts)==6 and all(type(x) is int and 0<=x<2**64 for x in counts) and counts[0]>0,'resident counts')
  _require(abs(counts[1]-ir)<=max(1000,.01*ir),'resident retired instruction mismatch')
 return dict(condition=c['name'],args=c['args'],config=rr[0],program=rr[1],runtime=runtime,samples=rr[3:])

def analyze(run):
 """Signed paired effect, absolute within-process stability, no discarded windows."""
 _fields(run,dict(mode=MODE,processes=15),'resident matrix identity');rows=run.get('rows');_require(type(rows) is list and len(rows)==15,'resident matrix coverage');points=[];blocks=[];ratios=[]
 for r,c in zip(rows,conditions()):
  _fields(r,dict(condition=c['name'],args=c['args']),'resident condition order')
  audit_process([r['config'],r['program'],r['runtime'],*r['samples']],c,plans());a,link,n,rev=identity(c);epoch=int(c['name'][1]);by={(s['block'],s['preparation']):s for s in r['samples']}
  for preparation in ('resident','reinstall'):
   values=[by[b,preparation]['counts'][0]/ITERATIONS for b in range(8)];spread=(max(values)-min(values))/st.median(values)
   points.append(dict(epoch=epoch,anchor=a,link=link,n=n,preparation=preparation,cycles=values,median=st.median(values),range_fraction=spread,stable=spread<=.10))
  for b in range(8):
   resident=by[b,'resident']['counts'][0]/ITERATIONS;reinstall=by[b,'reinstall']['counts'][0]/ITERATIONS;delta=reinstall-resident
   blocks.append(dict(epoch=epoch,anchor=a,link=link,n=n,block=b,resident=resident,reinstall=reinstall,delta=delta,relative_delta=delta/resident))
  for s in r['samples']:
   counts=s['counts'];ratios.append(dict(condition=c['name'],position=s['position'],block=s['block'],preparation=s['preparation'],counts=counts,cycles_per_iter=counts[0]/ITERATIONS,ns=s['ns'],cycles_per_ns=counts[0]/s['ns'],**{hex(event):counts[j]/counts[0] for j,event in enumerate(EVENTS) if j>=2}))
 summaries=[]
 for a,link,n in SPECS:
  bb=[b for b in blocks if (b['anchor'],b['link'],b['n'])==(a,link,n)];pp=[p for p in points if (p['anchor'],p['link'],p['n'])==(a,link,n)]
  stable={v:all(p['stable'] for p in pp if p['preparation']==v) for v in ('resident','reinstall')}
  effect='maintenance-associated-increase' if all(b['delta']>2 and b['relative_delta']>.05 for b in bb) else 'maintenance-associated-decrease' if all(b['delta']<-2 and b['relative_delta']<-.05 for b in bb) else 'effect-not-replicated'
  state='resident-supply-still-variable' if not stable['resident'] else 'maintenance-condition-associated-instability' if not stable['reinstall'] else 'both-conditions-stable-in-this-protocol'
  summaries.append(dict(anchor=a,link=link,n=n,within_process_stable=stable,maintenance_effect=effect,state=state,delta=[b['delta'] for b in bb],delta_median=st.median(b['delta'] for b in bb),delta_range=[min(b['delta'] for b in bb),max(b['delta'] for b in bb)]))
 return dict(mode=MODE,windows=240,primary=summaries[1],conditions=summaries,points=points,blocks=blocks,window_ratios=ratios,physical_entries_certified=False,naming_limit='fixed-program pre-warmup maintenance association; carryover and variant switching not eliminated')

def audit_raw(path):
 """Launch/source/build/environment and complete raw inventory, never patched input."""
 inventory={'manifest.json','driver.py','consumer.py','environment-policy.json','initial-environment.json','final-environment.json'}|{c['name']+suffix for c in conditions() for suffix in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')}
 _require({p.name for p in path.iterdir()}==inventory and all(p.is_file() for p in path.iterdir()),'resident raw inventory')
 m=json.loads((path/'manifest.json').read_text());_fields(m,dict(mode=MODE,status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,build_evidence_path=BUILD,protocol_path=PROTOCOL,plan_path=PLAN,consumer_path=CONSUMER),'resident manifest identity')
 _require(_same(m.get('conditions'),conditions()) and type(m.get('results')) is list and len(m['results'])==15,'resident requested/result coverage')
 blob=lambda ref,p:subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT);sha=lambda b:hashlib.sha256(b).hexdigest();head=m['source_head']
 for file,key in ((DRIVER,'driver_sha256'),(CONSUMER,'consumer_sha256'),(PROTOCOL,'protocol_sha256'),(BUILD,'build_evidence_sha256'),(PLAN,'plan_sha256')):_require(sha(blob(head,file))==m[key],'resident launch SHA '+file)
 for saved,key in (('driver.py','driver_sha256'),('consumer.py','consumer_sha256')):_require(sha((path/saved).read_bytes())==m[key],'resident saved '+saved)
 build=json.loads(blob(head,BUILD));registered=json.loads(blob(head,PLAN));validate_plan(registered)
 _require(build['binaries']['rob_resident_control']==m['binary_sha256'] and build['source_commit']==m['binary_source_head'] and build['plan_sha256']==m['plan_sha256'],'resident binary/source/plan binding')
 for file,digest in build['source_sha256'].items():_require(sha(blob(head,file))==digest and sha(blob(m['binary_source_head'],file))==digest,'resident source dependency '+file)
 from tools.diagnostic.analyze_long_load import audit_environment
 profile=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'));policy=profile['environment_profiles']['charging-thermal']['measurement_environment'];policy['preconditions']['cpufreq_governor']='walt'
 env={p.name:json.loads(p.read_text()) for p in path.glob('*-environment.json')};audit_environment(env,json.loads((path/'environment-policy.json').read_text()),policy)
 rows=[]
 for r,c in zip(m['results'],conditions()):
  _fields(r,dict(name=c['name'],exit_code=0,timed_out=False),'resident result identity/status');f=path/(c['name']+'.stdout.jsonl')
  _require(sha(f.read_bytes())==r['stdout_sha256'] and (path/(c['name']+'.stderr.log')).read_bytes()==b'','resident stdout/stderr')
  rows.append(audit_process([json.loads(l) for l in f.read_text().splitlines()],c,registered))
 return dict(mode=MODE,processes=15,source_branch=m['source_branch'],source_head=head,binary_source_head=m['binary_source_head'],binary_sha256=m['binary_sha256'],raw_directory=path.name,manifest_sha256=sha((path/'manifest.json').read_bytes()),max_cpu_c_range=[min(v['snapshot']['thermal']['max_cpu_c'] for v in env.values()),max(v['snapshot']['thermal']['max_cpu_c'] for v in env.values())],rows=rows),{p.name:sha(p.read_bytes()) for p in sorted(path.iterdir())}
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--summary-output',type=Path,required=True);a=p.parse_args(argv)
 run,hashes=audit_raw(a.raw);result=analyze(run);s=json.dumps(run,indent=2,allow_nan=False)+'\n';result.update(data_origin='device-raw',input_sha256=hashlib.sha256(s.encode()).hexdigest(),all_raw_sha256=hashes);a.summary_output.write_text(s);a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(windows=result['windows'],primary=result['primary'])))
if __name__=='__main__':main()
