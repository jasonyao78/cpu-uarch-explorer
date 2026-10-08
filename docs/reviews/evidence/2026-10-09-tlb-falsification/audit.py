# SPDX-License-Identifier: Apache-2.0
# Read-only raw/record audit for the three preserved private exploration epochs.
from pathlib import Path
import json,sys,hashlib,statistics
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from runner.adapters.ptr_chase import PtrChaseAdapter
from analysis.sm8650_tlb_a1_contract import expected_cases,validate_record
from analysis.sm8650_tlb_a1_freeze import load_audited_run
from runner.environment.policy import evaluate_preconditions_full,evaluate_stability_full
adapter=PtrChaseAdapter()
paths=['data/private/20261008T165359Z-sm8650-tlb-controls','data/private/20261008T165531Z-sm8650-tlb-scan','data/private/20261008T220015Z-sm8650-tlb-followup']
summary={'schema':'exploratory-derived-summary-v1','purpose':'falsification and effective local transition; no formal H* or physical ways','target':'redmi-k70pro-01','profile':'exploration-stock-walt-v1','page_kb':4,'rounds_per_process':20,'valid_rounds_per_process':19,'repetitions_per_condition':5,'epochs':[]}
allraw=set();maxdiff=0
for rel in paths:
 p=ROOT/rel;m=json.loads((p/'exploration-manifest.json').read_text());assert m['status']=='completed'
 policy=json.loads((p/'platform-input.json').read_text())['measurement_environment']
 epoch={'directory':rel,'manifest_sha256':hashlib.sha256((p/'exploration-manifest.json').read_bytes()).hexdigest(),'created_utc':m['created_utc'],'binary_sha256':m['binary_sha256'],'source_head':m['source_head'],'driver_sha256':m['driver_sha256'],'conditions':[]}
 specs={c['label']:c for c in m['conditions']}
 for r in m['results']:
  label=r['label'];specpath=p/specs[label]['spec']
  assert hashlib.sha256(specpath.read_bytes()).hexdigest()==specs[label]['sha256']
  records,_=load_audited_run(p/r['run_dir']);assert len(records)==1
  rec=records[0];exp=expected_cases(specpath,'exploration-'+label)[0];met=validate_record(rec,exp)
  assert all(e['type']==8 for e in exp.params['pmu_events']) and len(exp.params['pmu_events'])==6
  env=rec['environment']['state_snapshot'];assert env['policy_result']['valid'] and not env['policy_result']['violations'] and not env['policy_result']['accepted_nonbaseline']
  for state in ('before','after'):
   v,w=evaluate_preconditions_full(env[state],policy);assert not v and not w
  v,w=evaluate_stability_full(env['before'],env['after'],policy);assert not v and not w
  artifacts={a['id']:a for a in map(json.loads,(p/r['run_dir']/'artifacts.jsonl').read_text().splitlines())}
  raw=[]
  for s in rec['probe']['realized']['samples']:
   i=s['sample_index'];entry=artifacts[s['raw_sample_ref']]
   out=Path(entry['path'].replace('{stdout,stderr}','stdout')).read_bytes()
   err=Path(entry['path'].replace('{stdout,stderr}','stderr')).read_bytes()
   payload=out+b'\n--- stderr ---\n'+err;digest=hashlib.sha256(payload).hexdigest()
   assert digest==entry['sha256'] and len(payload)==entry['size_bytes']
   assert entry['id'] not in allraw;allraw.add(entry['id'])
   parsed=adapter.parse_output(out.decode(),err.decode(),exp.params)
   real=adapter.parse_realized(out.decode(),exp.params);assert real==s['realized']
   assert real['set_region_vpn_hi_pure']==1 and real['set_domain']=='multi-region'
   for metric in parsed:
    obs=next(o for o in met[metric['name']]['observations'] if o['sample_index']==i)
    assert metric['value']==obs['value'] and metric['unit']==met[metric['name']]['unit']
   assert next(x['value'] for x in parsed if x['name']=='window_valid_rounds')==19
   assert all(next(x['value'] for x in parsed if x['name']==n)==0 for n in ('window_invalid_rounds','window_mux_rounds'))
   raw.append({'sample_index':i,'sha256':digest,'size_bytes':len(payload)})
  obs={name:[o['value'] for o in sorted(x['observations'],key=lambda o:o['sample_index'])] for name,x in met.items()}
  for refill,dwalk,iwalk in zip(obs['pmu.l2d_tlb_refill.count'],obs['pmu.dtlb_walk.count'],obs['pmu.itlb_walk.count']):maxdiff=max(maxdiff,abs(refill-dwalk-iwalk))
  params={k:v for k,v in exp.params.items() if k not in ('pmu_events',)}
  epoch['conditions'].append({'label':label,'params':params,'metrics':obs,'raw_sha256':raw,'source_dirty':rec['probe']['git']['dirty'],'temperature_before_c':env['before']['thermal']['max_cpu_c'],'temperature_after_c':env['after']['thermal']['max_cpu_c'],'wall_seconds':r['wall_seconds'],'input_spec_sha256':specs[label]['sha256']})
 epoch['process_count']=sum(len(x['raw_sha256']) for x in epoch['conditions'])
 epoch['wall_seconds_sum']=sum(c['wall_seconds'] for c in epoch['conditions'])
 summary['epochs'].append(epoch)
summary['audit']={'process_count':len(allraw),'valid_round_count':len(allraw)*19,'raw_sha_size_reparse_realized_metrics_match':True,'max_abs_refill_minus_data_instruction_walk':round(maxdiff,8),'all_conditions_environment_valid':True,'all_windows_19_valid_0_invalid_0_mux':True}
assert len(allraw)==185
out=Path('/private/tmp/sm8650-tlb-falsification-summary-20261009.json');out.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(summary['audit']))
for e in summary['epochs']:
 print(e['directory'],'wall',round(e['wall_seconds_sum'],2),'temp_range',min(min(c['temperature_before_c'],c['temperature_after_c']) for c in e['conditions']),max(max(c['temperature_before_c'],c['temperature_after_c']) for c in e['conditions']))
 for c in e['conditions']:
  d=c['metrics']['pmu.dtlb_walk.count'];print(c['label'],d,'median',statistics.median(d))
print('DERIVED',out)
