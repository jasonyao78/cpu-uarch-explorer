"""Immutable source/binary/actual C layouts and BPF words -> complete original graph raw.

Contract docs/design/2026-10-13-tlb-observed-reach.md. Scan must retain the exact
qualified prior input and same binary; missing/stopped/rehashed corruption never promotes.
"""
import copy,hashlib,json,subprocess,tempfile
from pathlib import Path
from tools.diagnostic import tlb_observed_reach_analysis as model
from runner.environment.policy import evaluate_preconditions_full
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit_raw(raw):
 raw=Path(raw);m=json.loads((raw/'manifest.json').read_text());need=model.need;phase=m.get('phase');cc=model.conditions(phase);need(m.get('mode')==model.MODE and m.get('btf_sha256')==model.BTF_SHA and m.get('target')=='redmi-k70pro-01','observed raw mode/BTF/target');need(m.get('status') in ('complete','capability-unavailable','technical-failure','not-excited'),'observed stopped/partial raw');entries=m.get('results');need(type(entries)is list and 1<=len(entries)<=len(cc),'observed process coverage');need(model.exact(m.get('conditions'),cc),'observed requested conditions')
 if m['status']=='complete':need(len(entries)==len(cc),'observed full matrix required')
 need([e.get('name') for e in entries]==[c['name'] for c in cc[:len(entries)]],'observed result identity/order/duplicate');head=m['source_head'];source=m['binary_source_head'];blob=lambda ref,rel:subprocess.check_output(['git','show',ref+':'+rel],cwd=ROOT);digest=lambda b:hashlib.sha256(b).hexdigest();build=json.loads(blob(head,model.BUILD));registered=json.loads(blob(head,model.PLAN));need(model.exact(registered,model.plans()) and digest(blob(head,model.PLAN))==m['plan_sha256']==build['actual_plan_sha256'],'observed actual layout plan');need(m['binary_sha256']==build['binary_sha256'] and source==build['source_commit'] and m['build_sha256']==digest(blob(head,model.BUILD)),'observed binary/build')
 for rel,value in build['source_sha256'].items():need(digest(blob(source,rel))==value==digest(blob(head,rel)),'observed source dependency '+rel)
 for saved,field,rel in (('driver.py','driver_sha256',model.DRIVER),('consumer.py','consumer_sha256',model.CONSUMER)):need(sha(raw/saved)==m[field]==digest(blob(head,rel)),'observed registered saved '+saved)
 need(m['protocol_sha256']==digest(blob(head,model.PROTOCOL)),'observed protocol')
 prior=m.get('qualification_input')
 if phase=='qualification':need(prior is None,'observed qualification cannot borrow prior')
 else:
  need(type(prior)is dict and type(prior.get('raw_directory'))is str,'observed qualified prior required');p=Path(prior['raw_directory']);need(p.resolve()!=raw.resolve() and sha(p/'manifest.json')==prior['manifest_sha256'],'observed prior manifest');q,h=audit_raw(p);need(q['phase']=='qualification' and model.analyze(q)['status']=='OBSERVED_GRAPH_QUALIFIED' and q['binary_sha256']==m['binary_sha256'] and model.exact(h,prior['raw_sha256']),'observed immutable qualified prior')
 profile=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'));policy=copy.deepcopy(profile['environment_profiles']['charging-thermal']['measurement_environment']);policy['preconditions']['cpufreq_governor']='walt';need(model.exact(json.loads((raw/'environment-policy.json').read_text()),policy),'observed environment policy');inventory={'manifest.json','host-plan','driver.py','consumer.py','environment-policy.json','initial-environment.json','final-environment.json'}|{e['name']+suffix for e in entries for suffix in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')};rows=[]
 with tempfile.TemporaryDirectory() as t:
  td=Path(t)
  for rel in ('probes/diagnostic/tlb_observed_reach.c','probes/diagnostic/translation_persistent_bpf.h','probes/diagnostic/translation_persistent_gate.h','probes/common/perf_group_read.h'):
   target=td/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(blob(source,rel))
  host=td/'producer';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(td/'probes/diagnostic/tlb_observed_reach.c'),'-o',str(host)],check=True,capture_output=True)
  for n in model.GRID:
   for r in (0,1):need(model.exact(json.loads(subprocess.check_output([str(host),'--plan','--nodes',str(n),'--reverse',str(r)],text=True)),registered[f'{n}:{r}']),'observed immutable native layout')
  for i,(e,c) in enumerate(zip(entries,cc)):
   name=e['name'];f=raw/(name+'.stdout.jsonl');need(e.get('timed_out') is False and sha(f)==e['stdout_sha256'],'observed timeout/stdout SHA');rr=[json.loads(l) for l in f.read_text().splitlines()];need(rr and all(type(r)is dict for r in rr),'observed raw record objects');program=None
   if len(rr)>1 and rr[0].get('probe')==model.MODE:
    pp=rr[1];program=json.loads(subprocess.check_output([str(host),'--bpf-plan',str(pp['owner_pid']),str(pp['map_fd'])],text=True));inventory.add(name+'-actual-plan.json');need(model.exact(json.loads((raw/(name+'-actual-plan.json')).read_text()),program),'observed persisted byteplan')
   row=model.audit_process(rr,program,c,registered);need(e.get('status')==row['status'],'observed saved status')
   if row['status']=='complete':need(type(e.get('exit_code'))is int and e['exit_code']==0 and not(raw/(name+'.stderr.log')).read_text(),'observed success status/stderr')
   else:need(type(e.get('exit_code'))is int and i==len(entries)-1 and e['exit_code']==(0 if row['status']=='NOT_EXCITED' else 1),'observed first failure/empty must stop')
   rows.append(row)
 need({p.name for p in raw.iterdir()}==inventory and all(p.is_file() for p in raw.iterdir()),'observed raw inventory');env=[]
 for name in ['initial','final',*[e['name']+'-'+s for e in entries for s in ('pre','post')]]:
  d=json.loads((raw/(name+'-environment.json')).read_text());v,w=evaluate_preconditions_full(d['snapshot'],policy);need(not v and not w and d.get('violations')==v and d.get('warnings')==w,'observed environment '+name);env.append(d)
 if m['status']=='complete':need(all(v['status']=='complete' for v in rows),'observed full qualified rows')
 else:need(rows[-1]['status']=={'not-excited':'NOT_EXCITED','capability-unavailable':'CAPABILITY_UNAVAILABLE','technical-failure':'TECHNICAL_FAILURE'}[m['status']],'observed failure status')
 hashes={p.name:sha(p) for p in sorted(raw.iterdir()) if p.name not in ('host-plan','manifest.json')};return dict(mode=model.MODE,phase=phase,status=m['status'],rows=rows,source_head=head,binary_source_head=source,binary_sha256=m['binary_sha256'],source_branch=m['source_branch'],manifest_sha256=sha(raw/'manifest.json'),raw_directory=raw.name,max_cpu_c_range=[min(d['snapshot']['thermal']['max_cpu_c'] for d in env),max(d['snapshot']['thermal']['max_cpu_c'] for d in env)]),hashes
