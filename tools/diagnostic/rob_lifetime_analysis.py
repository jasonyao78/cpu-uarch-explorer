#!/usr/bin/env python3
"""E0发现后的盲留E2预测；不改原ROB容量判据，不认证physical entries。

冻结：docs/design/2026-10-12-rob-lifetime-heldout.md。调用原消费者审计全矩阵，
只让E2的四条NOP-eligible曲线决定新预测是否复制；原取指门结果单独保留。
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from tools.diagnostic import rob_zero_units_analysis as original
from tools.diagnostic.analyze_cold_pair import _require
PROTOCOL='docs/design/2026-10-12-rob-lifetime-heldout.md'
REGISTRATION='docs/reviews/evidence/2026-10-12-rob-lifetime-heldout/registration.json'
PATTERNS=('nop-pair','nop-movzero');PREDICTIONS={16:[336,352],32:[320,336]}

def analyze(run):
 """完整硬审计产物→固定E2预测；任何删失/背景/供给不合格均命名降级。"""
 _require(run.get('phase')=='scan','lifetime full scan required');primary=original.analyze(run)
 points={(p['epoch'],p['anchor'],p['pattern'],p['groups'],p['chain']):p for p in primary['points']}
 records={r['condition']:r for r in run['rows']};i0=min(x for p in primary['points'] if p['anchor']=='independent' and p['groups']==0 and p['chain']==16 for x in p['cycles']);curves=[];cache_failures=[]
 for pattern in PATTERNS:
  for chain in (16,32):
   comparisons=[];states=[];grid=original.GRIDS[pattern][2:]
   for g in grid:
    pp=[points[2,a,pattern,g,k] for a,k in (('none',16),('serial',chain),('independent',chain))];nv,sv,iv=[p['cycles'] for p in pp];frontend=[]
    for p in pp:
     name=f"e2-{p['anchor']}-{pattern}-g{g}-k{p['chain']}";rr=records[name]
     for sample in rr['samples']:
      ratio=sample['counts'][4]/sample['counts'][0];frontend.append(ratio)
      if sample['counts'][5]/original.ITERATIONS>.001:cache_failures.append(dict(condition=name,position=sample['position'],refills_per_iter=sample['counts'][5]/original.ITERATIONS))
    stable=all(p['stable'] for p in pp);supply=max(nv)<=.90*i0;front=max(frontend)<=.01;ok=primary['qualified'] and stable and supply and front
    state='INCOMPUTABLE' if not ok else 'near-serial' if min(iv)>=.95*max(sv) and max(iv)<=1.05*min(sv) else 'overlap-retained' if max(iv)<.90*min(sv) else 'ambiguous';states.append(state)
    comparisons.append(dict(groups=g,state=state,none_cycles=nv,serial_cycles=sv,independent_cycles=iv,stable=stable,supply=supply,frontend_fraction=frontend,frontend_condition_passed=front))
   interval=None
   if 'INCOMPUTABLE' in states:status='INCOMPUTABLE'
   elif any(states[i]=='near-serial' and 'overlap-retained' in states[i+1:] for i in range(len(states))):status='nonmonotonic'
   elif 'ambiguous' in states:status='ambiguous'
   elif 'near-serial' not in states:status='no-saturation-through-grid'
   elif states[0]=='near-serial':status='left-censored'
   else:
    i=states.index('near-serial')
    if i==len(states)-1:status='right-censored'
    else:status='interval';interval=[grid[i-1],grid[i]]
   curves.append(dict(epoch=2,pattern=pattern,chain=chain,status=status,interval=interval,predicted_interval=PREDICTIONS[chain],matched=status=='interval' and interval==PREDICTIONS[chain],candidate_proxy_interval=[g+chain for g in interval] if interval else None,points=comparisons))
 status='LIFETIME_PROXY_PREDICTION_REPLICATED' if all(c['matched'] for c in curves) else 'PREDICTION_NOT_REPLICATED' if all(c['status']=='interval' for c in curves) else 'INCONCLUSIVE'
 # 同一NONE曲线供两chain对照，公开失败列表去重不意味着删任何窗口。
 unique={(x['condition'],x['position']):x for x in cache_failures}
 return dict(status=status,discovery_epoch=0,excluded_confirmation_epoch=1,validation_epoch=2,original_status=primary['status'],original_qualification=primary['qualification'],original_icache_failures=[unique[k] for k in sorted(unique)],curves=curves,proxy_interval=[352,368] if status=='LIFETIME_PROXY_PREDICTION_REPLICATED' else None,physical_entries_certified=False,allocation_units_certified=False,naming_limit='one blinded epoch replicates candidate eligible-group + chain proxy; original cache gate remains rejected, active resource and physical allocation are not certified')

def main(argv=None):
 """实际raw完整审计+发现SHA绑定→留出结果；不接受补拼或不同发现目录。"""
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('raw',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv)
 run,hashes=original.audit_raw(a.raw);registration=json.loads((ROOT/REGISTRATION).read_text())
 _require(registration['raw_directory']==a.raw.name and registration['epoch2_records_at_freeze']==0 and registration['completed_processes_at_freeze']<196 and registration['discovery_epoch']==0 and registration['validation_epoch']==2 and registration['excluded_from_confirmation_epoch']==1,'lifetime frozen split')
 _require(len(registration['all_epoch0_sha256'])==98 and all(hashes.get(p)==s for p,s in registration['all_epoch0_sha256'].items()),'lifetime discovery SHA')
 result=analyze(run);result.update(data_origin='device-raw',source_branch=run['source_branch'],binary_source_head=run['binary_source_head'],launch_head=run['source_head'],analysis_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),raw_directory=a.raw.name,all_raw_sha256=hashes,protocol_sha256=hashlib.sha256((ROOT/PROTOCOL).read_bytes()).hexdigest(),registration_sha256=hashlib.sha256((ROOT/REGISTRATION).read_bytes()).hexdigest(),consumer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(status=result['status'],proxy_interval=result['proxy_interval'],physical_entries_certified=False)))
if __name__=='__main__':main()
