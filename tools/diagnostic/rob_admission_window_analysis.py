"""Growing-gap issue evidence, not an allocation or physical-ROB entry ruler."""
import statistics as st
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
from tools.diagnostic import rob_register_fenced_analysis as register
from tools.diagnostic import rob_fenced_issue_analysis as marker
from tools.diagnostic.rob_direct_fenced_analysis import check_roi
MODE='rob-admission-window';EVIDENCE='docs/reviews/evidence/2026-10-14-rob-admission-window'
PROTOCOL='docs/design/2026-10-14-rob-admission-window.md';CONSUMER='tools/diagnostic/rob_admission_window_analysis.py';DRIVER='tools/diagnostic/run_sm8650_rob_admission_window.py'
GAPS=list(range(0,769,128));FILLERS=['sink','zero','nop'];OPS=[0x8b02003f,0xd280000a,0xd503201f]
def program(chain,gap,filler,mode,idx):
 w=register.program_words(chain,mode,idx);j=30+chain+4;w[j]=0xb500000c|((19+gap)<<5);at=30+chain+14;return w[:at]+[OPS[FILLERS.index(filler)]]*gap+w[at:]
def expected(chain,gap,filler,idx=register.DEFAULT_INDICES):
 p=register.expected(chain,idx);p[0].update(probe=MODE,gap=gap,filler=filler)
 for mode,z in enumerate(p[1:5]):
  w=program(chain,gap,filler,mode,idx);z.update(words=w,code_bytes=len(w)*4,warm_words=register.warm_words(chain,w))
 return p
def plans():return {f'{k}-{n}-{f}':expected(k,n,f) for k in (16,32) for f in FILLERS for n in GAPS}
def conditions():
 grid=[(k,f,n) for k in (16,32) for f in FILLERS for n in GAPS]
 return [dict(name=f'e{e}-k{k}-{f}-n{n}',args=['--run','--chain',str(k),'--gap',str(n),'--filler',f]) for e in range(2) for k,f,n in (grid if e==0 else reversed(grid))]
def audit_process(rr,c,registered):
 _require(_same(registered,plans()),'admission native registered plans');k=int(c['args'][2]);gap=int(c['args'][4]);filler=c['args'][6];_require(type(rr)is list and len(rr)>=2 and _same(rr[0],expected(k,gap,filler)[0]),'admission config')
 if rr[-1].get('type')=='failure':
  _require(rr[-1].get('metrics')=={} and type(rr[-1].get('failure'))is dict,'admission failure');return dict(condition=c['name'],args=c['args'],status='TECHNICAL_FAILURE',failure=rr[-1]['failure'])
 _require(len(rr)==263,'admission full windows');runtime=rr[5];idx=register.indices(runtime.get('counter_indices'));want=expected(k,gap,filler,idx);_require(_same(rr[:5],want[:5]),'admission actual JIT words');_fields(runtime,dict(type='runtime',cpu=7,fpcr=0,hwcap_sb=True),'admission target')
 addrs=[runtime.get(n+'_base') for n in ('code','near','far','output')];_require(all(type(v)is int and v>0 and v%4096==0 for v in addrs) and len(set(addrs))==4,'admission own addresses');_require(runtime.get('hardware_buffer_base')==addrs[3]+64,'admission own timestamp buffer');ids=runtime.get('event_ids');_require(type(ids)is list and len(ids)==6 and len(set(ids))==6 and all(type(v)is int and 0<v<1<<64 for v in ids),'admission own IDs')
 binding=runtime.get('initial_binding');_require(type(binding)is list and len(binding)==6,'admission own binding')
 for v,i in zip(binding,idx):_require(v.get('cap')is True and v.get('index')==i and type(v.get('index'))is int and v.get('width')==64 and type(v.get('sequence_before'))is int and v['sequence_before']==v.get('sequence_after') and not(v['sequence_before']&1) and type(v.get('offset'))is int,'admission initial live metadata')
 def pfn(v):_require(type(v)is int and 0<=v<1<<64 and v>>63 and not(v&(1<<62)) and v&((1<<55)-1),'admission PFN');return v&((1<<55)-1)
 a=runtime.get('pagemap_before');b=rr[-1].get('pagemap_after');_require(type(a)is list and type(b)is list and len(a)==len(b)==4 and [pfn(v) for v in a]==[pfn(v) for v in b] and len(set(pfn(v) for v in a))==4 and rr[-1].get('fds_closed')is True,'admission final PFN/FD')
 for z,s in zip(rr[6:-1],want[5:]):
  active=s['control']=='architect' and s['marker']=='taps';arch=0x12345678 if active else 0;_fields(z,dict(s,type='round',result_bits=s['test_bits'],status_raw=0,near_architectural=arch,far_architectural_words=[arch]*8,code_base=addrs[0],code_matches_plan=True),'admission originals');_require(type(z.get('enabled'))is int and z['enabled']>0 and z['running']==z['enabled'],'admission noMUX');check_roi(z);_require([v['index'] for v in z['roi_before']]==idx,'admission actual current words')
 return dict(condition=c['name'],args=c['args'],status='complete',config=rr[0],programs=rr[1:5],runtime=runtime,samples=rr[6:-1],final=rr[-1])
def analyze(rows):
 _require(len(rows)==84,'admission full 84 processes');out=[]
 for row,c in zip(rows,conditions()):
  _require(row['condition']==c['name'] and row['status']=='complete','admission process identity');cells={(z['trial'],z['control'],z['fence'],z['marker']):z for z in row['samples']};dd={};gates={};thresholds={};cal={}
  for ctl in ('architect','speculate'):
   for fence in ('pre','post'):dd[ctl+'-'+fence]={hex(event):[cells[t,ctl,fence,'taps']['counts'][ix]-cells[t,ctl,fence,'nop']['counts'][ix] for t in range(32)] for ix,event in enumerate(marker.EVENTS)}
  for name,event in (('near','0x70'),('far','0x71')):
   aa=[dd['architect-'+f][event] for f in ('pre','post')];b=dd['speculate-pre'][event];lo=min(marker.quantile(v,.1) for v in aa);hi=marker.quantile(b,.9);gates[name+'_architect']=all(7<=st.mean(v)<=9 and marker.quantile([abs(x-8) for x in v],.9)<=3 for v in aa);gates[name+'_negative']=abs(st.mean(b))<=1 and marker.quantile([abs(x) for x in b],.9)<=3;gates[name+'_separable']=lo-hi>=4;thresholds[name]=(lo+hi)/2 if gates[name+'_separable'] else None;cal[name]=dict(architect_q10_min=lo,negative_q90=hi,architect_means=[st.mean(v) for v in aa],negative_mean=st.mean(b))
  gates['ir_matched']=all(abs(st.mean(dd[key]['0x8']))<=2 for key in dd);gates['ir_fence_matched']=all(abs(st.mean(cells[t,'speculate','post',m]['counts'][1]-cells[t,'speculate','pre',m]['counts'][1] for t in range(32)))<=2 for m in ('nop','taps'))
  supply=all(st.median([cells[t,ctl,f,m]['counts'][5] for t in range(32)])<=1 and marker.quantile([cells[t,ctl,f,m]['counts'][5] for t in range(32)],.95)<=4 for ctl in ('architect','speculate') for f in ('pre','post') for m in ('nop','taps'))
  eligible=[t for t in range(32) if thresholds['near']is not None and dd['speculate-post']['0x70'][t]>=thresholds['near']];respond=[t for t in eligible if thresholds['far']is not None and dd['speculate-post']['0x71'][t]>=thresholds['far']];rate=len(respond)/len(eligible) if eligible and thresholds['far']is not None else None
  grade='MARKER_NOT_QUALIFIED' if not all(gates.values()) else 'SUPPLY_NOT_QUALIFIED' if not supply else 'DEADLINE_NOT_OBSERVED' if len(eligible)<8 else 'reached' if rate>=.9 else 'blocked' if rate<=.1 else 'transition'
  out.append(dict(name=c['name'],chain=row['config']['chain'],gap=row['config']['gap'],filler=row['config']['filler'],classification=grade,calibration=cal,gates=gates,supply_qualified=supply,thresholds=thresholds,eligible_trials=eligible,responding_trials=respond,far_given_near_rate=rate,deltas=dd,cycle_medians={ctl+'-'+f+'-'+m:st.median(cells[t,ctl,f,m]['counts'][0] for t in range(32)) for ctl in ('architect','speculate') for f in ('pre','post') for m in ('nop','taps')}))
 curves=[]
 for e in range(2):
  for k in (16,32):
   for f in FILLERS:
    points=sorted((x for x in out if x['name'].startswith(f'e{e}-') and x['chain']==k and x['filler']==f),key=lambda x:x['gap']);reach=[x['gap'] for x in points if x['classification']=='reached'];block=[x['gap'] for x in points if x['classification']=='blocked'];invalid=any(x['classification'] not in ('reached','blocked','transition') for x in points);nonmono=any(b<a for a in reach for b in block);lo=max(reach) if reach else None;hi=min((b for b in block if lo is None or b>lo),default=None)
    curves.append(dict(epoch=e,chain=k,filler=f,points=[dict(gap=x['gap'],classification=x['classification'],rate=x['far_given_near_rate']) for x in points],status='INCOMPUTABLE' if invalid else 'nonmonotonic' if nonmono else 'left-censored' if lo is None else 'right-censored' if hi is None else 'bracketed',last_reached=lo,first_later_blocked=hi))
 return dict(mode=MODE,status='ADMISSION_MATRIX_COMPLETE',windows=21504,processes=out,curves=curves,physical_capacity_certified=False,ROB_allocation_units_certified=False)
