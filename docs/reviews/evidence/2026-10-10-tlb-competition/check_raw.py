import json,hashlib,statistics,collections,sys
from pathlib import Path
raw,summary_path,model_path,out=map(Path,sys.argv[1:])
s=json.loads(summary_path.read_text());m=json.loads(model_path.read_text());manifest=json.loads((raw/'manifest.json').read_text())
def mean(a):
 a=list(a);return sum(a)/len(a)
all_rows=[];by={};epochs=[]
for e in range(5):
 records=[json.loads(l) for l in (raw/f'epoch-{e}.stdout.jsonl').read_text().splitlines()]
 rr=[r for r in records if r['type']=='round'];assert len(rr)==7296
 for r in rr:
  key=(f'epoch-{e}',r['h'],r['k'],r['direction'],r['passes'],r['role'],r['pass_index'])
  by.setdefault(key,[]).append(r['counts'])
 all_rows+=rr
 epochs.append(dict(epoch=e,records=len(records),windows=len(rr),wall_seconds=manifest['results'][e]['wall_seconds']))
for p in m['lookup_points']:
 key=(p['epoch'],p['h'],p['k'],p['direction'],p['passes'],'competition',p['pass_index'])
 arr=by[key];k0=(key[0],key[1],0,*key[3:]);control=by[k0]
 assert len(arr)==len(control)==16
 counts=[[x[j] for x in arr] for j in range(6)];controls=[[x[j] for x in control] for j in range(6)]
 diffs=[mean(a)-mean(b) for a,b in zip(counts,controls)]
 assert (counts,controls,diffs)==(p['counts'],p['control_counts'],p['count_mean_differences'])
 assert p['observable']==all(.75*p['k']<=diffs[j]<=1.25*p['k'] for j in (1,3))
for p in m['victim_points']:
 issues=[];rates={}
 ok=all(mean(x[4]>0 for x in by[p['epoch'],h,0,p['direction'],p['passes'],'victim',p['passes']])<=.125 for h in (1,2))
 if not ok:issues.append('baseline-contaminated')
 for h in (1,2):
  a=by[p['epoch'],h,p['k'],p['direction'],p['passes'],'victim',p['passes']];walk=[x[4] for x in a]
  drift=mean(x>0 for x in walk[8:])-mean(x>0 for x in walk[:8]);rate=mean(x>0 for x in walk);rates[h]=rate
  assert p['families'][str(h)]==dict(counts=a,walk=walk,response_rate=rate,walk_mean=mean(walk),rate_drift=drift,count_over_one=sum(x>1 for x in walk))
  if any(x>1 for x in walk):issues.append('single-load-window-residual')
  if abs(drift)>.25:issues.append('preparation-drift')
 issues=list(dict.fromkeys(issues));diff=rates[1]-rates[2]
 assert p['issues']==issues and p['difference']==diff and p['baseline_ok']==ok and p['response_observed']==(not issues and diff>=.5)
for p in m['replication']:
 names=[f'epoch-{e}' for e in range(5) if all(next(v for v in m['victim_points'] if (v['epoch'],v['k'],v['direction'],v['passes'])==(f'epoch-{e}',p['k'],d,p['passes']))['response_observed'] for d in (0,1))]
 assert names==p['epoch_names'] and len(names)==p['epochs'] and p['passed']==(len(names)>=4)
 assert p['all_related_lookups_observable']==all(x['observable'] for x in m['lookup_points'] if (x['k'],x['passes'])==(p['k'],p['passes']))
assert m['input_sha256']==hashlib.sha256(summary_path.read_bytes()).hexdigest()
assert len(all_rows)==36480
hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(raw.iterdir()) if p.is_file()}
assert len(hashes)==25
env=[]
for p in sorted(raw.glob('*-environment.json')):
 x=json.loads(p.read_text());assert not x['warnings'] and not x['violations']
 snap=x['snapshot'];env.append(dict(endpoint=p.name,max_cpu_c=snap['thermal']['max_cpu_c'],policy7=snap['cpufreq']['policy7']))
receipt=dict(independent_raw_math_passed=True,author='root independent direct JSONL arithmetic; no separate reviewer',windows=len(all_rows),lookup_points=len(m['lookup_points']),observable=sum(p['observable'] for p in m['lookup_points']),victim_points=len(m['victim_points']),replication_points=len(m['replication']),replication_passed=sum(p['passed'] for p in m['replication']),all_raw_sha256=hashes,epochs=epochs,environment_endpoints=env,
 all_event_statistics=[dict(event=hex(ev),minimum=min(r['counts'][i] for r in all_rows),maximum=max(r['counts'][i] for r in all_rows),nonzero=sum(r['counts'][i]>0 for r in all_rows),sum=sum(r['counts'][i] for r in all_rows)) for i,ev in enumerate((17,5,45,47,52,53))],
 refill_equals_walk_sum=all(r['counts'][2]==r['counts'][4]+r['counts'][5] for r in all_rows),
 role_statistics={role:dict(windows=sum(r['role']==role for r in all_rows),datawalk_nonzero=sum(r['role']==role and r['counts'][4]>0 for r in all_rows),datawalk_over_one=sum(r['role']==role and r['counts'][4]>1 for r in all_rows),itlb_nonzero=sum(r['role']==role and r['counts'][5]>0 for r in all_rows)) for role in ('competition','victim')},
 source_head=manifest['source_head'],binary_source_head=manifest['binary_source_head'],source_branch=manifest['source_branch'],binary_sha256=manifest['binary_sha256'])
out.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:receipt[k] for k in ('windows','lookup_points','observable','victim_points','replication_points','replication_passed','role_statistics')}))
print('lookup failures', collections.Counter((p['h'],p['k'],p['passes']) for p in m['lookup_points'] if not p['observable']))
print('victim issues',collections.Counter(i for p in m['victim_points'] for i in p['issues']))
for p in m['replication']:print(p)
