"""Resource response with fixed ordinals and one named metadata-invalid packet."""
import statistics as st
from tools.diagnostic import rob_filler_resource_batch_analysis as old
from tools.diagnostic import owned_roi_packets as packets
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
MODE='rob-filler-resource-bounded';EVIDENCE='docs/reviews/evidence/2026-10-14-rob-filler-resource-bounded'
PROTOCOL='docs/design/2026-10-14-bounded-owned-roi-packets.md';CONSUMER='tools/diagnostic/rob_filler_resource_bounded_analysis.py';DRIVER='tools/diagnostic/run_sm8650_rob_filler_resource_bounded.py'
def expected(n,f,idx=old.hot.base.register.DEFAULT_INDICES):
 p=old.expected(n,f,idx);p[0].update(version=5,probe=MODE,max_metadata_invalid_packets=1);return p
def plans():return {f'{n}-{f}':expected(n,f) for n in (32,64) for f in (0,4,8,12)}
def conditions():return old.conditions()
def audit_process(rr,c,registered):
 _require(_same(registered,plans()),'bounded resource native plans');n=int(c['args'][2]);f=int(c['args'][4]);_require(type(rr)is list and len(rr)>=2 and _same(rr[0],expected(n,f)[0]),'bounded resource config')
 if rr[-1].get('type')=='failure':_require(rr[-1].get('metrics')=={},'bounded resource failure metrics');return dict(condition=c['name'],args=c['args'],status='TECHNICAL_FAILURE',failure=rr[-1]['failure'])
 idx=old.hot.base.register.indices(rr[5].get('counter_indices'));want=expected(n,f,idx);_require(_same(rr[:5],want[:5]),'bounded resource actual words');runtime=packets.runtime(rr,idx);parsed=packets.decode(rr[6:-1],want[5:]);packets.final_counts(rr[-1],parsed);formal=[];warm=[]
 for block in parsed['valid']+parsed['invalid']:
  s=block['schedule'];role=dict(control=s['control'],unit=s['unit'],input_bits=s['input_bits'],result_bits=s['input_bits'],checksum=n*0x12345678,reserved_output=(runtime['near_base']+runtime['far_base'])&((1<<64)-1) if s['unit']=='live' and f else 0)
  for ordinal,z in enumerate(block['warm']):_fields(z,dict(type='warm-roi',trial=s['trial'],position=s['position'],ordinal=ordinal,**role),'bounded resource warm originals')
  if 'sample' in block:
   z=block['sample'];_fields(z,dict(s,type='round',**role,code_base=runtime['code_base'],code_matches_plan=True),'bounded resource formal originals');packets.audit_envelope([*block['warm'],z],idx);formal.append(z);warm.extend(block['warm'])
  else:
   packets.validate_rejection(block['rejected'],idx)
   if block['warm']:packets.audit_envelope(block['warm'],idx)
 return dict(condition=c['name'],args=c['args'],status='complete',config=rr[0],programs=rr[1:5],runtime=runtime,samples=formal,warmup_windows=warm,invalid_packets=parsed['invalid'],final=rr[-1])
def analyze(rows):
 _require(len(rows)==16,'bounded resource16 processes');out=[];positive=[];supply=[];ir=[];total=warms=invalid=0
 for row,c in zip(rows,conditions()):
  _require(row['condition']==c['name'] and row['status']=='complete','bounded resource identity');n=row['config']['chain'];f=row['config']['filler'];cells={(z['trial'],z['control'],z['unit']):z for z in row['samples']};med={};mad={};paired={};gates={};coverage={};total+=len(row['samples']);warms+=len(row['warmup_windows']);invalid+=len(row['invalid_packets'])
  for seed in ('seed-0','seed-1'):
   values={name:[cells[t,seed,name] for t in packets.paired_trials(cells,(seed,name))] for name in ('nop','sink','live','zero')};med[seed]={name:[st.median(z['counts'][j] for z in vv) for j in range(6)] for name,vv in values.items()};mad[seed]={name:[st.median(abs(z['counts'][j]-med[seed][name][j]) for z in vv) for j in range(6)] for name,vv in values.items()}
   for name,vv in values.items():
    v=sorted(z['counts'][5] for z in vv);supply.append(st.median(v)<=1 and v[int(.95*len(v))]<=4);tt=packets.paired_trials(cells,(seed,name),(seed,'nop'));ir.append(all(abs(cells[t,seed,name]['counts'][1]-cells[t,seed,'nop']['counts'][1])<=2 for t in tt))
   paired[seed]={};coverage[seed]={}
   for a,b in (('sink','zero'),('live','zero'),('sink','nop')):
    tt=packets.paired_trials(cells,(seed,a),(seed,b));paired[seed][a+'-'+b]=[cells[t,seed,a]['counts'][0]-cells[t,seed,b]['counts'][0] for t in tt];coverage[seed][a+'-'+b]=tt
   v=paired[seed]['sink-zero'];gates[seed]=st.median(v)>=8 and sum(x>0 for x in v)/len(v)>=.8
  if f in (8,12):positive.append(all(gates.values()))
  out.append(dict(name=c['name'],chain=n,filler=f,valid_packets=len(row['samples']),invalid_packets=len(row['invalid_packets']),medians=med,MAD=mad,paired_cycles=paired,paired_trials=coverage,resource_gates=gates))
 return dict(mode=MODE,status='TECHNICAL_FAILURE' if not all(ir) else 'SUPPLY_NOT_QUALIFIED' if not all(supply) else 'REPEATABLE_FILLER_RESOURCE_EFFECT' if all(positive) else 'RESOURCE_EFFECT_NOT_ESTABLISHED',attempted_packets=4096,windows=total,owned_warm_windows=warms,invalid_packets=invalid,processes=out,IR_equal=all(ir),supply_qualified=all(supply),physical_capacity_certified=False,ROB_allocation_units_certified=False)
