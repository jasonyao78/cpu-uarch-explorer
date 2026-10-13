"""One owned perf_user_access 0->1->0 write-ahead transaction, always persisted.

docs/design/2026-10-13-pmu-enabled-metadata.md. Never edit journal state manually.
"""
import json,os,uuid
from datetime import datetime,timezone
from pathlib import Path
SYSCTL='/proc/sys/kernel/perf_user_access'
TERMINAL={'restored'}
def durable_write(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.tmp-'+uuid.uuid4().hex)
 with tmp.open('x') as f:f.write(json.dumps(data,indent=2)+'\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path);fd=os.open(path.parent,os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
class PerfUserAccessTransaction:
 def __init__(self,executor,path):self.executor=executor;self.path=Path(path);self.journal=None
 def read(self):
  r=self.executor.execute(['su','-c','cat '+SYSCTL]);value=r.stdout.strip()
  if r.returncode or r.timed_out or r.stderr or value not in ('0','1'):raise RuntimeError('perf-user-access read failed')
  return int(value)
 def save(self):durable_write(self.path,self.journal)
 def write(self,value,kind):
  if type(value)is not int or value not in (0,1):raise ValueError('registered policy values only')
  cmd=['su','-c',f'printf {value} > {SYSCTL}'];self.journal[kind+'_intent']=cmd;self.save();r=self.executor.execute(cmd);self.journal[kind+'_result']=dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr,timed_out=r.timed_out);self.save()
  if r.returncode or r.timed_out or r.stderr:raise RuntimeError('perf-user-access write failed '+kind)
 def restore(self):
  if self.journal is None:self.journal=json.loads(self.path.read_text())
  j=self.journal
  if j.get('mutation')!='sysctl.perf_user_access' or j.get('target')!='redmi-k70pro-01' or type(j.get('baseline'))is not int or j['baseline']!=0:raise RuntimeError('unowned/unsupported restore journal')
  if j.get('state')=='restored':
   if self.read()!=j['baseline']:raise RuntimeError('terminal journal cannot overwrite a later profile')
   return
  j['state']='restoring';self.save()
  try:
   current=self.read();j['restore_before']=current
   if current!=j['baseline']:self.write(j['baseline'],'restore')
   after=self.read();j['restore_after']=after
   if after!=j['baseline']:raise RuntimeError('restore verification mismatch')
   j['state']='restored';j['restored_at']=datetime.now(timezone.utc).isoformat()
  except BaseException as e:j['state']='restore-failed';j['restore_error']=repr(e);raise RuntimeError('perf-user-access restore failed: '+str(e)) from e
  finally:self.save()
 def run(self,work,provenance=None):
  if self.path.exists():raise RuntimeError('transaction exists; explicit restore required')
  baseline=self.read()
  if baseline!=0:raise RuntimeError('baseline must be registered 0; no overwrite')
  self.journal=dict(version=1,mutation='sysctl.perf_user_access',target='redmi-k70pro-01',baseline=baseline,requested=1,state='created',created_at=datetime.now(timezone.utc).isoformat(),provenance=provenance);self.save()
  try:
   self.write(1,'apply');actual=self.read();self.journal['applied_actual']=actual
   if actual!=1:raise RuntimeError('apply verification mismatch')
   self.journal['state']='applied';self.save();result=work();self.journal['work_complete']=True;self.save();return result
  except BaseException as e:self.journal['work_error']=repr(e);self.save();raise
  finally:self.restore()
