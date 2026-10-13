"""Candidate filler µop semantics; execution operations are not ROB allocations."""
import statistics
from tools.diagnostic.analyze_cold_pair import _require,_same
from tools.diagnostic import rob_register_fenced_analysis as register
from tools.diagnostic.rob_direct_fenced_analysis import check_roi
MODE='rob-filler-resource';EVIDENCE='docs/reviews/evidence/2026-10-14-rob-filler-resource'
PROTOCOL='docs/design/2026-10-14-rob-filler-resource.md';CONSUMER='tools/diagnostic/rob_filler_resource_analysis.py';DRIVER='tools/diagnostic/run_sm8650_rob_filler_resource.py'
NAMES=['nop','sink','live','zero'];OPS=[0xd503201f,0x8b02003f,0x8b02002a,0xd280000a]
def body(chain,filler,mode):return [0xaa1f03e9,0xaa1f03ea]+sum(([OPS[mode]]*filler+[0x8b040129] for _ in range(chain)),[])+[0xa9002869,0xd50330ff,0xd65f03c0]
def program(chain,filler,mode,idx):
 w=register.program_words(16,0,idx);return w[:30]+body(chain,filler,mode)[:-1]+w[-36:]
def expected(chain,filler,idx=register.DEFAULT_INDICES):
 idx=register.indices(idx);cfg=register.expected(16)[0];cfg.update(probe=MODE,chain=chain,filler=filler,events=[17,8,58,59,115,1]);pp=[]
 for mode,name in enumerate(NAMES):
  w=program(chain,filler,mode,idx);pp.append(dict(type='program',unit=name,code_bytes=4*len(w),words=w,counter_indices=idx,warm_words=register.warm_words(chain,w)))
 schedule=[]
 for t in range(32):
  for pos in range(8):
   i=(t+pos)%8;i=7-i if (t//8)%2 else i;schedule.append(dict(type='schedule',trial=t,position=pos,control='seed-'+str(i//4),unit=NAMES[i%4],input_bits=i//4))
 return [cfg,*pp,*schedule]
def conditions():
 grid=[(n,f) for n in (32,64) for f in (0,4,8,12)]
 return [dict(name=f'e{e}-c{n}-f{f}',args=['--run','--chain',str(n),'--filler',str(f)]) for e in range(2) for n,f in (grid if e==0 else reversed(grid))]
def audit_process(rr,c,plans):
 _require(_same(plans,{f'{n}-{f}':expected(n,f) for n in (32,64) for f in (0,4,8,12)}),'unit actual native plans');n=int(c['args'][2]);f=int(c['args'][4]);_require(type(rr)is list and len(rr)>=2 and _same(rr[0],expected(n,f)[0]),'unit config')
 if rr[-1].get('type')=='failure':return dict(condition=c['name'],args=c['args'],status='TECHNICAL_FAILURE',failure=rr[-1]['failure'])
 _require(len(rr)==263,'unit all windows');runtime=rr[5];idx=register.indices(runtime.get('counter_indices'));want=expected(n,f,idx);_require(_same(rr[:5],want[:5]),'unit actual generated programs')
 _require(runtime.get('cpu')==7 and runtime.get('hardware_buffer_base')==runtime['output_base']+64,'unit runtime');a=runtime.get('pagemap_before');b=rr[-1].get('pagemap_after');_require(type(a)is list and type(b)is list and len(a)==len(b)==4 and all(type(v)is int and v>>63 and not v&(1<<62) and v&((1<<55)-1) for v in a+b) and [v&((1<<55)-1) for v in a]==[v&((1<<55)-1) for v in b] and rr[-1].get('fds_closed')is True,'unit PFN/final')
 for z,s in zip(rr[6:-1],want[5:]):
  _require(all(_same(z.get(k),v) for k,v in dict(s,type='round',result_bits=s['input_bits'],checksum=n*0x12345678,reserved_output=(runtime['near_base']+runtime['far_base'])&((1<<64)-1) if s['unit']=='live' and f else 0,code_base=runtime['code_base'],code_matches_plan=True).items()),'unit schedule/checksum')
  _require(type(z.get('enabled'))is int and z['enabled']>0 and _same(z.get('running'),z['enabled']),'unit noMUX');check_roi(z);_require([v['index'] for v in z['roi_before']]==idx,'unit current bound words')
 return dict(condition=c['name'],args=c['args'],config=rr[0],programs=rr[1:5],runtime=runtime,samples=rr[6:-1],final=rr[-1],status='complete')
def analyze(rows):
 _require(len(rows)==16,'resource all 16 fresh processes');process=[];positive=[];supply=[];ir=[]
 for row,c in zip(rows,conditions()):
  _require(row['condition']==c['name'] and row['status']=='complete','resource process identity');n=row['config']['chain'];f=row['config']['filler'];cells={(z['trial'],z['control'],z['unit']):z for z in row['samples']};med={};mad={};paired={};gates={}
  for seed in ('seed-0','seed-1'):
   med[seed]={name:[statistics.median(cells[t,seed,name]['counts'][j] for t in range(32)) for j in range(6)] for name in NAMES}
   mad[seed]={name:[statistics.median(abs(cells[t,seed,name]['counts'][j]-med[seed][name][j]) for t in range(32)) for j in range(6)] for name in NAMES}
   for name in NAMES:
    v=sorted(cells[t,seed,name]['counts'][5] for t in range(32));supply.append(statistics.median(v)<=1 and v[30]<=4)
    ir.append(all(abs(cells[t,seed,name]['counts'][1]-cells[t,seed,'nop']['counts'][1])<=2 for t in range(32)))
   paired[seed]={a+'-'+b:[cells[t,seed,a]['counts'][0]-cells[t,seed,b]['counts'][0] for t in range(32)] for a,b in (('sink','zero'),('live','zero'),('sink','nop'))}
   v=paired[seed]['sink-zero'];gates[seed]=statistics.median(v)>=8 and sum(x>0 for x in v)/32>=.8
  if f in (8,12):positive.append(all(gates.values()))
  process.append(dict(name=c['name'],chain=n,filler=f,medians=med,MAD=mad,paired_cycles=paired,resource_gates=gates))
 technical=all(ir);code_supply=all(supply);qualified=technical and code_supply and all(positive)
 return dict(mode=MODE,status='TECHNICAL_FAILURE' if not technical else 'SUPPLY_NOT_QUALIFIED' if not code_supply else 'REPEATABLE_FILLER_RESOURCE_EFFECT' if qualified else 'RESOURCE_EFFECT_NOT_ESTABLISHED',windows=4096,processes=process,IR_equal=technical,supply_qualified=code_supply,physical_capacity_certified=False,ROB_allocation_units_certified=False)
