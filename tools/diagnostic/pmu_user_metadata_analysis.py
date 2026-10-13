"""Own perf metadata intake; no MRS eligibility or counter semantics promoted."""
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
MODE='pmu-user-metadata';PROTOCOL='docs/design/2026-10-13-pmu-user-metadata.md';BUILD='docs/reviews/evidence/2026-10-13-pmu-user-metadata/build.json';PLAN='docs/reviews/evidence/2026-10-13-pmu-user-metadata/plan.json';DRIVER='tools/diagnostic/run_sm8650_pmu_user_metadata.py';CONSUMER='tools/diagnostic/pmu_user_metadata_analysis.py';EVENTS=(17,8,112,113)
def conditions():return [dict(name=f'e{e}-f{f}',args=['--run','--config1',str(f)]) for e in range(3) for f in ((2,3) if e%2==0 else (3,2))]
def expected(flag):return dict(probe=MODE,version=1,events=list(EVENTS),config1=flag,cpu=7,pmu_type=8,metadata_only=True,counter_register_reads=0,global_policy_mutation=False,own_thread_only=True,pinned_group=True,exclude_kernel=True,exclude_hv=True)
def audit_process(rr,c,plan):
 _require(_same(plan,{str(f):expected(f) for f in (2,3)}),'metadata actual plans');flag=int(c['args'][2]);_require(type(rr)is list and len(rr)>=2 and all(type(v)is dict for v in rr) and _same(rr[0],expected(flag)),'metadata producer plan');last=rr[-1]
 if last.get('type')=='failure':
  _fields(last,dict(metrics={},fds_closed=True,global_policy_mutation=False,counter_register_reads=0),'metadata failure cleanup');f=last.get('failure');_require(type(f)is dict and type(f.get('reason'))is str and type(f.get('errno'))is int,'metadata failure object');_require(len(rr) in (2,3,4),'metadata first failure coverage');policy=rr[1].get('perf_user_access') if rr[1].get('type')=='policy' else None
  if policy is not None:_require(type(policy)is int and policy in (0,1) and rr[1].get('read_only')is True,'metadata policy')
  return dict(status='CAPABILITY_UNAVAILABLE' if f['reason'] in ('perf-open-user-config','perf-metadata-map') else 'TECHNICAL_FAILURE',failure=f,policy=policy,counter_read_qualified=False)
 _require(len(rr)==4,'metadata complete record coverage');policy=rr[1];_fields(policy,dict(type='policy',read_only=True),'metadata policy');value=policy.get('perf_user_access');_require(type(value)is int and value in (0,1),'metadata actual policy');d=rr[2];_fields(d,dict(type='metadata',cpu=7),'metadata runtime');ev=d.get('events');_require(type(ev)is list and len(ev)==4,'metadata event coverage');ids=[]
 for row,event in zip(ev,EVENTS):
  _fields(row,dict(event=event),'metadata event identity');_require(type(row.get('id'))is int and 0<row['id']<1<<64 and type(row.get('cap_user_rdpmc'))is bool,'metadata id/cap');ids.append(row['id']);_require(all(type(row.get(k))is int and 0<=row[k]<1<<64 for k in ('index','pmc_width','offset','sequence_before','sequence_after')) and row['index']<=32 and row['pmc_width'] in (0,32,64),'metadata unsigned fields')
 _require(len(set(ids))==4,'metadata unique own IDs');_fields(last,dict(type='final',fds_closed=True,global_policy_mutation=False,counter_register_reads=0,counter_read_qualified=False),'metadata final')
 return dict(status='ACCESS_DISABLED' if value==0 else 'METADATA_INTAKE_COMPLETE',policy=value,events=ev,counter_read_qualified=False,physical_capacity_certified=False)
