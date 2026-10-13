"""Candidate filler µop semantics; execution operations are not ROB allocations."""
import statistics
from tools.diagnostic.analyze_cold_pair import _require,_same
from tools.diagnostic import rob_register_fenced_analysis as register
from tools.diagnostic.rob_direct_fenced_analysis import check_roi
MODE='rob-sink-unit';EVIDENCE='docs/reviews/evidence/2026-10-14-rob-sink-unit'
PROTOCOL='docs/design/2026-10-14-rob-sink-unit.md';CONSUMER='tools/diagnostic/rob_sink_unit_analysis.py';DRIVER='tools/diagnostic/run_sm8650_rob_sink_unit.py'
NAMES=['nop','sink','live','zero'];OPS=[0xd503201f,0x8b02003f,0x8b020029,0xd2800009]
def body(count,mode):return [0xaa1f03e9]+[OPS[mode]]*count+[0xf9000069,0xd65f03c0]
def program(count,mode,idx):
 # Replace only the recipe's body; prefix/suffix are audited register templates.
 w=register.program_words(16,0,idx);return w[:30]+body(count,mode)[:-1]+w[-36:]
def expected(count,idx=register.DEFAULT_INDICES):
 idx=register.indices(idx);cfg=register.expected(16)[0];cfg.pop('chain');cfg.update(probe=MODE,count=count,events=[17,8,58,59,115,1]);pp=[]
 for mode,name in enumerate(NAMES):
  w=program(count,mode,idx);pp.append(dict(type='program',unit=name,code_bytes=4*len(w),words=w,counter_indices=idx,warm_words=register.warm_words(count,w)))
 schedule=[]
 for t in range(32):
  for pos in range(8):
   i=(t+pos)%8;i=7-i if (t//8)%2 else i;schedule.append(dict(type='schedule',trial=t,position=pos,control='seed-'+str(i//4),unit=NAMES[i%4],input_bits=i//4))
 return [cfg,*pp,*schedule]
def conditions():return [dict(name=f'e{e}-n{n}',args=['--run','--count',str(n)]) for e in range(3) for n in ((16,32) if e%2==0 else (32,16))]
def audit_process(rr,c,plans):
 _require(_same(plans,{str(n):expected(n) for n in (16,32)}),'unit actual native plans');n=int(c['args'][2]);_require(type(rr)is list and len(rr)>=2 and _same(rr[0],expected(n)[0]),'unit config')
 if rr[-1].get('type')=='failure':return dict(condition=c['name'],args=c['args'],status='TECHNICAL_FAILURE',failure=rr[-1]['failure'])
 _require(len(rr)==263,'unit all windows');runtime=rr[5];idx=register.indices(runtime.get('counter_indices'));want=expected(n,idx);_require(_same(rr[:5],want[:5]),'unit actual generated programs')
 _require(runtime.get('cpu')==7 and runtime.get('hardware_buffer_base')==runtime['output_base']+64,'unit runtime');a=runtime.get('pagemap_before');b=rr[-1].get('pagemap_after');_require(type(a)is list and type(b)is list and len(a)==len(b)==4 and all(type(v)is int and v>>63 and not v&(1<<62) and v&((1<<55)-1) for v in a+b) and [v&((1<<55)-1) for v in a]==[v&((1<<55)-1) for v in b] and rr[-1].get('fds_closed')is True,'unit PFN/final')
 for z,s in zip(rr[6:-1],want[5:]):
  _require(all(_same(z.get(k),v) for k,v in dict(s,type='round',result_bits=s['input_bits'],checksum=(runtime['near_base']+runtime['far_base'])&((1<<64)-1) if s['unit']=='live' else 0,reserved_output=0,code_base=runtime['code_base'],code_matches_plan=True).items()),'unit schedule/checksum')
  _require(type(z.get('enabled'))is int and z['enabled']>0 and _same(z.get('running'),z['enabled']),'unit noMUX');check_roi(z);_require([v['index'] for v in z['roi_before']]==idx,'unit current bound words')
 return dict(condition=c['name'],args=c['args'],config=rr[0],programs=rr[1:5],runtime=runtime,samples=rr[6:-1],final=rr[-1],status='complete')
def analyze(rows):
 _require(len(rows)==6,'unit process coverage');process=[];slopes=[];by={}
 for row,c in zip(rows,conditions()):
  _require(row['condition']==c['name'],'unit process identity');n=row['config']['count'];cells={(z['trial'],z['control'],z['unit']):z for z in row['samples']};checks={};med={};deltas={}
  for seed in ('seed-0','seed-1'):
   med[seed]={name:[statistics.median(cells[t,seed,name]['counts'][j] for t in range(32)) for j in range(6)] for name in NAMES}
   deltas[seed]={name:[[cells[t,seed,name]['counts'][j]-cells[t,seed,'nop']['counts'][j] for t in range(32)] for j in range(6)] for name in NAMES}
   for name in ('sink','live'):
    v=deltas[seed][name][4];checks[seed+'-'+name+'-DP']=abs(statistics.median(v)-n)<=1 and sum(abs(x-n)<=2 for x in v)>=30
  by[c['name']]=(med,checks);process.append(dict(name=c['name'],count=n,gates=checks,medians=med,deltas=deltas))
 for e in range(3):
  lo=by[f'e{e}-n16'][0];hi=by[f'e{e}-n32'][0]
  for seed in ('seed-0','seed-1'):
   for name in NAMES:
    v=[hi[seed][name][j]-lo[seed][name][j] for j in range(6)];qualified=name not in ('sink','live') or all(abs(v[j]-16)<=1 for j in (1,2,4));slopes.append(dict(epoch=e,seed=seed,unit=name,delta_n16=v,executed_one_uop=qualified if name in ('sink','live') else None))
 ok=all(all(p['gates'].values()) for p in process) and all(x['executed_one_uop']is not False for x in slopes)
 return dict(mode=MODE,status='SINK_EXECUTED_ONE_UOP_QUALIFIED' if ok else 'SINK_UNIT_NOT_QUALIFIED',windows=1536,processes=process,slopes=slopes,physical_capacity_certified=False,ROB_allocation_units_certified=False)
