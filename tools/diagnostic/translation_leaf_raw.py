"""Re-read all raw owned-leaf records against immutable producer/launch inputs.

Contract: docs/design/2026-10-12-translation-self-leaf.md. Compiles the source
at binary_source_head to rederive each dynamic instruction plan; never trusts a
record's self-reported bytecode or silently promotes a stopped/partial run.
"""
import copy,hashlib,json,subprocess,tempfile
from pathlib import Path
from tools.diagnostic import translation_leaf_analysis as model
from runner.environment.policy import evaluate_preconditions_full
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit_raw(raw):
 raw=Path(raw);m=json.loads((raw/'manifest.json').read_text());need=model.need
 need(m.get('mode')==model.MODE and m.get('btf_sha256')==model.BTF_SHA,'raw mode/BTF identity')
 need(m.get('status') in ('complete','capability-unavailable','technical-failure','not-excited'),'stopped or partial raw')
 launch=m.get('source_head');source=m.get('binary_source_head');need(type(launch)is str and type(source)is str,'commit provenance')
 def blob(ref,rel):return subprocess.check_output(['git','show',ref+':'+rel],cwd=ROOT)
 b=json.loads(blob(launch,model.BUILD));need(m.get('binary_sha256')==b['binary_sha256'] and source==b['source_commit'] and m.get('build_sha256')==hashlib.sha256(blob(launch,model.BUILD)).hexdigest(),'binary/build provenance')
 for file,field,rel in [('driver.py','driver_sha256',model.DRIVER),('consumer.py','consumer_sha256',model.CONSUMER)]:
  need(sha(raw/file)==m.get(field)==hashlib.sha256(blob(launch,rel)).hexdigest(),'raw registered '+file)
 need(m.get('protocol_sha256')==hashlib.sha256(blob(launch,model.PROTOCOL)).hexdigest(),'protocol drift')
 profile=json.loads(blob(launch,'configs/platforms/redmi-k70pro-01.json'));policy=copy.deepcopy(profile['environment_profiles']['charging-thermal']['measurement_environment']);policy['preconditions']['cpufreq_governor']='walt';need(model.exact(json.loads((raw/'environment-policy.json').read_text()),policy),'environment policy drift')
 entries=m.get('results');need(type(entries)is list and 1<=len(entries)<=3,'process coverage')
 if m['status']=='complete':need(len(entries)==3,'complete needs three processes')
 need([e.get('name') for e in entries]==['epoch-'+str(i) for i in range(len(entries))],'process identity/order/duplicate')
 hashes={};verdicts=[]
 with tempfile.TemporaryDirectory() as td:
  td=Path(td)
  for rel in ('probes/diagnostic/translation_self_leaf.c','probes/diagnostic/translation_leaf_bpf.h'):
   content=blob(source,rel);need(hashlib.sha256(content).hexdigest()==b['source_sha256'][rel],'binary source drift');(td/Path(rel).name).write_bytes(content)
  host=td/'producer';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(td/'translation_self_leaf.c'),'-o',str(host)],check=True,capture_output=True)
  for i,e in enumerate(entries):
   name=e['name'];f=raw/(name+'.stdout.jsonl');need(sha(f)==e.get('stdout_sha256'),'stdout SHA');need(e.get('timed_out') is False,'probe timeout');rr=[json.loads(s) for s in f.read_text().splitlines()];plan=None
   if len(rr)==1 and rr[0].get('type')=='leaf-read':
    pp=rr[0]['program'];plan=json.loads(subprocess.check_output([str(host),'--plan',str(pp['owner_pid']),str(pp['selected_va']),str(pp['map_fd'])],text=True));need(model.exact(json.loads((raw/(name+'-actual-plan.json')).read_text()),plan),'persisted dynamic plan')
   v=model.audit_process(rr,plan);need(model.exact(e.get('verdict'),v),'persisted verdict drift');verdicts.append(v)
   if v['status']=='SELF_LEAF_DESCRIPTOR_READ':need(e.get('exit_code')==0 and type(e['exit_code'])is int and not (raw/(name+'.stderr.log')).read_text(),'success status/stderr')
   else:need(type(e.get('exit_code'))is int and i==len(entries)-1 and (e['exit_code']==0 if v['status']=='NOT_EXCITED' else e['exit_code']!=0),'failure/empty hook must stop without retries')
 for name in ['initial','final',*[e['name']+'-'+side for e in entries for side in ('pre','post')]]:
  d=json.loads((raw/(name+'-environment.json')).read_text());v,w=evaluate_preconditions_full(d['snapshot'],policy);need(not v and not w and d.get('violations')==v and d.get('warnings')==w,'environment gate '+name)
 if m['status']=='complete':need(all(v['status']=='SELF_LEAF_DESCRIPTOR_READ' for v in verdicts),'incomplete qualification');status='SELF_LEAF_DESCRIPTOR_READ'
 elif m['status']=='not-excited':need(verdicts[-1]['status']=='NOT_EXCITED','excitation status');status='NOT_EXCITED'
 elif m['status']=='capability-unavailable':need(verdicts[-1]['status']=='CAPABILITY_UNAVAILABLE','denial status');status='CAPABILITY_UNAVAILABLE'
 else:need(verdicts[-1]['status']=='TECHNICAL_FAILURE','technical status');status='TECHNICAL_FAILURE'
 for p in raw.iterdir():
  if p.is_file() and p.name not in ('manifest.json','host-plan'):hashes[p.name]=sha(p)
 return dict(status=status,processes=len(entries),verdicts=verdicts,all_raw_sha256=hashes,source_branch=m['source_branch'],binary_source_head=source,launch_head=launch,binary_sha256=m['binary_sha256'],btf_sha256=model.BTF_SHA,steady_leaf_cont_state='UNKNOWN',hpa_state='UNKNOWN',physical_entries_certified=False)
