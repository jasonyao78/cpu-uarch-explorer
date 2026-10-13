"""Immutable own-event metadata evidence, not counter-read qualification."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
from tools.diagnostic import pmu_user_metadata_analysis as m
from tools.diagnostic.analyze_long_load import audit_environment
ROOT=Path(__file__).resolve().parents[2]
def audit_raw(raw):
 raw=Path(raw);d=json.loads((raw/'manifest.json').read_text());m._fields(d,dict(mode=m.MODE,phase='metadata',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,build_evidence_path=m.BUILD,protocol_path=m.PROTOCOL,plan_path=m.PLAN,consumer_path=m.CONSUMER),'metadata manifest');status=d.get('status');m._require(status in ('complete','access-disabled','capability-unavailable'),'metadata stopped run');cc=m.conditions();n=6 if status=='complete' else 1;rr=d.get('results');m._require(m._same(d.get('conditions'),cc) and type(rr)is list and len(rr)==n and [e.get('name') for e in rr]==[c['name'] for c in cc[:n]],'metadata coverage/order');inventory={'manifest.json','driver.py','consumer.py','environment-policy.json','initial-environment.json','final-environment.json'}|{c['name']+s for c in cc[:n] for s in ('.stdout.jsonl','.stderr.log','-pre-environment.json','-post-environment.json')};m._require({p.name for p in raw.iterdir()}==inventory and all(p.is_file() for p in raw.iterdir()),'metadata raw inventory')
 sha=lambda b:hashlib.sha256(b).hexdigest();blob=lambda ref,rel:subprocess.check_output(['git','show',ref+':'+rel],cwd=ROOT);head=d['source_head'];source=d['binary_source_head']
 for file,key in ((m.DRIVER,'driver_sha256'),(m.CONSUMER,'consumer_sha256'),(m.PROTOCOL,'protocol_sha256'),(m.BUILD,'build_evidence_sha256'),(m.PLAN,'plan_sha256')):m._require(sha(blob(head,file))==d[key],'metadata launch '+file)
 for file,key in (('driver.py','driver_sha256'),('consumer.py','consumer_sha256')):m._require(sha((raw/file).read_bytes())==d[key],'metadata saved '+file)
 build=json.loads(blob(head,m.BUILD));plan=json.loads(blob(head,m.PLAN));m._require(build['source_commit']==source and build['binary_sha256']==d['binary_sha256'] and build['plan_sha256']==d['plan_sha256'],'metadata binary/source/plan')
 for file,h in build['source_sha256'].items():m._require(sha(blob(head,file))==h==sha(blob(source,file)),'metadata source dependency '+file)
 with tempfile.TemporaryDirectory() as tmp:
  t=Path(tmp)
  for file in ('probes/diagnostic/pmu_user_reader.c','probes/common/perf_group_read.h'):
   p=t/file;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob(source,file))
  native=t/'native';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(t/'probes/diagnostic/pmu_user_reader.c'),'-o',str(native)],check=True,capture_output=True)
  for f in (2,3):m._require(m._same(json.loads(subprocess.check_output([str(native),'--plan','--config1',str(f)],text=True)),plan[str(f)]),'metadata actual immutable producer')
 profile=json.loads(blob(head,'configs/platforms/redmi-k70pro-01.json'));pol=profile['environment_profiles']['charging-thermal']['measurement_environment'];pol['preconditions']['cpufreq_governor']='walt';env={p.name:json.loads(p.read_text()) for p in raw.glob('*-environment.json')};audit_environment(env,json.loads((raw/'environment-policy.json').read_text()),pol);rows=[]
 for c,e in zip(cc,rr):
  m._fields(e,dict(name=c['name'],timed_out=False),'metadata result');f=raw/(c['name']+'.stdout.jsonl');m._require(sha(f.read_bytes())==e['stdout_sha256'],'metadata stdoutSHA');a=m.audit_process([json.loads(l) for l in f.read_text().splitlines()],c,plan);m._require(m._same(e.get('classification'),a),'metadata saved classification');m._require(type(e.get('exit_code'))is int and e['exit_code']==(1 if a['status']=='CAPABILITY_UNAVAILABLE' else 0),'metadata return');m._require((raw/(c['name']+'.stderr.log')).read_bytes()==b'','metadata stderr');rows.append(a)
 m._require(status=={'ACCESS_DISABLED':'access-disabled','CAPABILITY_UNAVAILABLE':'capability-unavailable','METADATA_INTAKE_COMPLETE':'complete'}[rows[-1]['status']],'metadata terminal classification');m._require(d.get('qualification_input')is None,'metadata prior forbidden');return dict(mode=m.MODE,status=status,processes=n,source_head=head,binary_source_head=source,binary_sha256=d['binary_sha256'],raw_directory=raw.name,rows=rows,counter_read_qualified=False),{p.name:sha(p.read_bytes()) for p in sorted(raw.iterdir())}
