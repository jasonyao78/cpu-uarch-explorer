"""Growing-gap issue evidence, not an allocation or physical-ROB entry ruler."""
import statistics as st
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
from tools.diagnostic import rob_register_fenced_analysis as register
from tools.diagnostic import rob_fenced_issue_analysis as marker
from tools.diagnostic.rob_direct_fenced_analysis import check_roi
from tools.diagnostic import owned_roi_packets as packets
MODE='rob-admission-window';EVIDENCE='docs/reviews/evidence/2026-10-14-rob-admission-window'
PROTOCOL='docs/design/2026-10-14-rob-admission-window.md';CONSUMER='tools/diagnostic/rob_admission_window_analysis.py';DRIVER='tools/diagnostic/run_sm8650_rob_admission_window.py'
GAPS=list(range(0,769,128));FILLERS=['sink','zero','nop'];OPS=[0x8b02003f,0xd280000a,0xd503201f]
def program(chain,gap,filler,mode,idx):
 w=register.program_words(chain,mode,idx);j=30+chain+4;w[j]=0xb500000c|((19+gap)<<5);at=30+chain+14;return w[:at]+[OPS[FILLERS.index(filler)]]*gap+w[at:]
def expected(chain,gap,filler,idx=register.DEFAULT_INDICES):
 p=register.expected(chain,idx);p[0].update(version=5,max_metadata_invalid_packets=1,probe=MODE,gap=gap,filler=filler,final_RX_owned_warm_calls=4,warm_protocol="post-RX-no-syscall-owned-ROI",fd_envelope="four-warm-plus-one-formal")
 for mode,z in enumerate(p[1:5]):
  w=program(chain,gap,filler,mode,idx);z.update(words=w,code_bytes=len(w)*4,warm_words=register.warm_words(chain,w))
 return p
def plans():return {f'{k}-{n}-{f}':expected(k,n,f) for k in (16,32) for f in FILLERS for n in GAPS}
def conditions():
 out=[]
 for phase in ('qualification','scan'):
  grid=[(k,f,n) for k in (16,32) for f in FILLERS for n in ([0] if phase=='qualification' else GAPS[1:])]
  out.extend(dict(name=f'e{e}-k{k}-{f}-n{n}',phase=phase,args=['--run','--chain',str(k),'--gap',str(n),'--filler',f]) for e in range(2) for k,f,n in (grid if e==0 else reversed(grid)))
 return out
def audit_process(rr,c,registered):
 _require(_same(registered,plans()),'admission native registered plans');k=int(c['args'][2]);gap=int(c['args'][4]);filler=c['args'][6];_require(type(rr)is list and len(rr)>=2 and _same(rr[0],expected(k,gap,filler)[0]),'admission config')
 if rr[-1].get('type')=='failure':
  _require(rr[-1].get('metrics')=={} and type(rr[-1].get('failure'))is dict,'admission failure');return dict(condition=c['name'],args=c['args'],status='TECHNICAL_FAILURE',failure=rr[-1]['failure'])
 _require(len(rr)>=6,'admission runtime');idx=register.indices(rr[5].get('counter_indices'));want=expected(k,gap,filler,idx);_require(_same(rr[:5],want[:5]),'admission actual JIT words');runtime=packets.runtime(rr,idx);parsed=packets.decode(rr[6:-1],want[5:]);packets.final_counts(rr[-1],parsed);formal=[];warm=[]
 for block in parsed['valid']+parsed['invalid']:
  sch=block['schedule'];arch=0x12345678 if sch['marker']=='taps' else 0
  for ordinal,z in enumerate(block['warm']):_fields(z,dict(type='warm-roi',trial=sch['trial'],position=sch['position'],ordinal=ordinal,control=sch['control'],marker=sch['marker'],fence=sch['fence'],train_bits=0,result_bits=0,status_raw=0,near_architectural=arch,far_architectural_words=[arch]*8),'admission warm originals')
  if 'sample' in block:
   z=block['sample'];arch=0x12345678 if sch['control']=='architect' and sch['marker']=='taps' else 0;_fields(z,dict(sch,type='round',result_bits=sch['test_bits'],status_raw=0,near_architectural=arch,far_architectural_words=[arch]*8,code_base=runtime['code_base'],code_matches_plan=True),'admission originals');packets.audit_envelope([*block['warm'],z],idx);formal.append(z);warm.extend(block['warm'])
  else:
   packets.validate_rejection(block['rejected'],idx)
   if block['warm']:packets.audit_envelope(block['warm'],idx)
 return dict(condition=c['name'],args=c['args'],status='complete',config=rr[0],programs=rr[1:5],runtime=runtime,samples=formal,warmup_windows=warm,invalid_packets=parsed['invalid'],final=rr[-1])
def classify_process(row,c):
 _require(row['condition']==c['name'] and row['status']=='complete','admission process identity');cells={(z['trial'],z['control'],z['fence'],z['marker']):z for z in row['samples']};dd={};paired={};gates={};thresholds={};cal={}
 for ctl in ('architect','speculate'):
  for fence in ('pre','post'):
   tt=packets.paired_trials(cells,(ctl,fence,'taps'),(ctl,fence,'nop'));paired[ctl+'-'+fence]=tt;dd[ctl+'-'+fence]={hex(event):[cells[t,ctl,fence,'taps']['counts'][ix]-cells[t,ctl,fence,'nop']['counts'][ix] for t in tt] for ix,event in enumerate(marker.EVENTS)}
 for name,event in (('near','0x70'),('far','0x71')):
  aa=[dd['architect-'+f][event] for f in ('pre','post')];b=dd['speculate-pre'][event];lo=min(marker.quantile(v,.1) for v in aa);hi=marker.quantile(b,.9);gates[name+'_architect']=all(7<=st.mean(v)<=9 and marker.quantile([abs(x-8) for x in v],.9)<=3 for v in aa);gates[name+'_negative']=abs(st.mean(b))<=1 and marker.quantile([abs(x) for x in b],.9)<=3;gates[name+'_separable']=lo-hi>=4;thresholds[name]=(lo+hi)/2 if gates[name+'_separable'] else None;cal[name]=dict(architect_q10_min=lo,negative_q90=hi,architect_means=[st.mean(v) for v in aa],negative_mean=st.mean(b))
 gates['ir_matched']=all(abs(st.mean(dd[key]['0x8']))<=2 for key in dd);gates['ir_fence_matched']=all(abs(st.mean(cells[t,'speculate','post',m]['counts'][1]-cells[t,'speculate','pre',m]['counts'][1] for t in packets.paired_trials(cells,('speculate','post',m),('speculate','pre',m))))<=2 for m in ('nop','taps'))
 supply=all(st.median([cells[t,ctl,f,m]['counts'][5] for t in packets.paired_trials(cells,(ctl,f,m))])<=1 and marker.quantile([cells[t,ctl,f,m]['counts'][5] for t in packets.paired_trials(cells,(ctl,f,m))],.95)<=4 for ctl in ('architect','speculate') for f in ('pre','post') for m in ('nop','taps'))
 near_by=dict(zip(paired['speculate-post'],dd['speculate-post']['0x70']));far_by=dict(zip(paired['speculate-post'],dd['speculate-post']['0x71']));eligible=[t for t in paired['speculate-post'] if thresholds['near']is not None and near_by[t]>=thresholds['near']];respond=[t for t in eligible if thresholds['far']is not None and far_by[t]>=thresholds['far']];rate=len(respond)/len(eligible) if eligible and thresholds['far']is not None else None
 grade='MARKER_NOT_QUALIFIED' if not all(gates.values()) else 'SUPPLY_NOT_QUALIFIED' if not supply else 'DEADLINE_NOT_OBSERVED' if len(eligible)<8 else 'reached' if rate>=.9 else 'blocked' if rate<=.1 else 'transition'
 response='DEADLINE_NOT_OBSERVED' if len(eligible)<8 or rate is None else 'reached' if rate>=.9 else 'blocked' if rate<=.1 else 'transition'
 return dict(marker_observable=all(gates.values()) and len(eligible)>=8 and rate is not None and rate>=.9,response=response,name=c['name'],chain=row['config']['chain'],gap=row['config']['gap'],filler=row['config']['filler'],classification=grade,calibration=cal,gates=gates,supply_qualified=supply,thresholds=thresholds,eligible_trials=eligible,responding_trials=respond,far_given_near_rate=rate,deltas=dd,paired_trials=paired,valid_packets=len(row['samples']),invalid_packets=len(row['invalid_packets']),cycle_medians={ctl+'-'+f+'-'+m:st.median(cells[t,ctl,f,m]['counts'][0] for t in packets.paired_trials(cells,(ctl,f,m))) for ctl in ('architect','speculate') for f in ('pre','post') for m in ('nop','taps')})
def analyze(rows):
 _require(len(rows)==84,'admission full 84 processes');out=[classify_process(row,c) for row,c in zip(rows,conditions())]
 curves=[]
 for e in range(2):
  for k in (16,32):
   for f in FILLERS:
    points=sorted((x for x in out if x['name'].startswith(f'e{e}-') and x['chain']==k and x['filler']==f),key=lambda x:x['gap']);reach=[x['gap'] for x in points if x['classification']=='reached'];block=[x['gap'] for x in points if x['classification']=='blocked'];invalid=any(x['classification'] not in ('reached','blocked','transition') for x in points);nonmono=any(b<a for a in reach for b in block);lo=max(reach) if reach else None;hi=min((b for b in block if lo is None or b>lo),default=None)
    observed_reach=[x['gap'] for x in points if x['response']=='reached'];observed_block=[x['gap'] for x in points if x['response']=='blocked'];observed_lo=max(observed_reach) if observed_reach else None;observed_hi=min((b for b in observed_block if observed_lo is None or b>observed_lo),default=None)
    curves.append(dict(epoch=e,chain=k,filler=f,points=[dict(gap=x['gap'],classification=x['classification'],response=x['response'],supply=x['supply_qualified'],rate=x['far_given_near_rate']) for x in points],status='INCOMPUTABLE' if invalid else 'nonmonotonic' if nonmono else 'left-censored' if lo is None else 'right-censored' if hi is None else 'bracketed',last_reached=lo,first_later_blocked=hi,observed_response_bracket=[observed_lo,observed_hi],observed_response_physical_capacity_certified=False))
 return dict(mode=MODE,status='ADMISSION_MATRIX_COMPLETE',attempted_packets=21504,windows=sum(len(r['samples']) for r in rows),owned_warm_windows=sum(len(r['warmup_windows']) for r in rows),invalid_packets=sum(len(r['invalid_packets']) for r in rows),processes=out,curves=curves,physical_capacity_certified=False,ROB_allocation_units_certified=False)
