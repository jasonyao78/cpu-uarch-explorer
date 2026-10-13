"""Oldest cold LDR heads: issued markers and long latency, never ROB slots."""
import copy,statistics as st
from tools.diagnostic import rob_admission_window_analysis as admission
from tools.diagnostic import owned_roi_packets as packets
from tools.diagnostic.analyze_cold_pair import _require,_same,_fields
MODE='rob-cold-head';EVIDENCE='docs/reviews/evidence/2026-10-14-rob-cold-head'
PROTOCOL='docs/design/2026-10-14-rob-cold-head-qualification.md';CONSUMER='tools/diagnostic/rob_cold_head_analysis.py';DRIVER='tools/diagnostic/run_sm8650_rob_cold_head.py'
PALETTES={'issue':[17,8,112,113,34,1],'cache':[17,8,112,113,3,23]}
def expected(h,p,state,idx=admission.register.DEFAULT_INDICES):
 _require(h in (1,2) and p in PALETTES and state in ('hot','cold'),'cold head frozen parameters');base=admission.expected(16,0,'sink',idx);cfg=base[0]
 for k in ('chain','filler','groups'):cfg.pop(k)
 cfg.update(probe=MODE,heads=h,palette=p,state=state,events=PALETTES[p]);programs=[]
 for mode,old in enumerate(base[1:5]):
  taps=mode%2;pre=mode<2;body=[0xaa1f03e9,0xd28acf06,0xf2a24686,0xf940008c]+([0xf940018c] if h==2 else [])+[0xb500026c,0xd50330ff if pre else 0xd503201f]+[0xf9400029+(j*8<<10) if taps else 0xd503201f for j in range(8)]+[0xf9000046+(j*8<<10) if taps else 0xd503201f for j in range(8)]+[0xd503201f if pre else 0xd50330ff,0xd50330ff,0xaa0c03e0,0xd53b442c,0xf900006c,0xf9000469];w=old['words'][:30]+body+old['words'][-36:];z=copy.deepcopy(old);z.update(words=w,code_bytes=len(w)*4,warm_words=admission.register.warm_words(h,w));programs.append(z)
 schedule=base[5:]
 for z in schedule:z['test_bits']=int(z['control']=='speculate')
 return [cfg,*programs,*schedule]
def plans():return {f'{h}-{p}-{s}':expected(h,p,s) for h in (1,2) for p in PALETTES for s in ('hot','cold')}
def conditions():
 grid=[(h,p,s) for h in (1,2) for p in PALETTES for s in ('hot','cold')];return [dict(name=f'e{e}-h{h}-{p}-{s}',args=['--run','--heads',str(h),'--palette',p,'--state',s]) for e in range(2) for h,p,s in (grid if e==0 else reversed(grid))]
def audit_process(rr,c,registered):
 _require(_same(registered,plans()),'cold native plans');h=int(c['args'][2]);palette=c['args'][4];state=c['args'][6];_require(type(rr)is list and len(rr)>=2 and _same(rr[0],expected(h,palette,state)[0]),'cold config')
 if rr[-1].get('type')=='failure':_require(rr[-1].get('metrics')=={},'cold failure');return dict(condition=c['name'],args=c['args'],status='TECHNICAL_FAILURE',failure=rr[-1]['failure'])
 idx=admission.register.indices(rr[5].get('counter_indices'));want=expected(h,palette,state,idx);_require(_same(rr[:5],want[:5]),'cold actual words');rt=packets.runtime(rr,idx);before=rt.get('head_pagemap_before');after=rr[-1].get('head_pagemap_after');_require(type(before)is list and type(after)is list and len(before)==len(after)==2,'cold head backing')
 def pfn(v):_require(type(v)is int and v>>63 and not(v&(1<<62)) and v&((1<<55)-1),'cold head visible PFN');return v&((1<<55)-1)
 _require([pfn(v) for v in before]==[pfn(v) for v in after] and len(set(pfn(v) for v in before+rt['pagemap_before']))==6,'cold head stable private maps');_require(all(type(rt.get(k))is int and rt[k]>0 and rt[k]%4096==0 for k in ('head_a_base','head_b_base')),'cold head addresses');_require(_same(rt.get('head_initial_values'),[rt['head_b_base'] if h==2 else 0,0]),'cold initial dependency links');parsed=packets.decode(rr[6:-1],want[5:]);packets.final_counts(rr[-1],parsed);formal=[];warm=[]
 for block in parsed['valid']+parsed['invalid']:
  sch=block['schedule'];arch=0x12345678 if sch['marker']=='taps' else 0
  for ordinal,z in enumerate(block['warm']):_fields(z,dict(type='warm-roi',trial=sch['trial'],position=sch['position'],ordinal=ordinal,control=sch['control'],marker=sch['marker'],fence=sch['fence'],train_bits=0,result_bits=0,status_raw=0,near_architectural=arch,far_architectural_words=[arch]*8),'cold warm originals')
  if 'sample' in block:
   z=block['sample'];arch=0x12345678 if sch['control']=='architect' and sch['marker']=='taps' else 0;_fields(z,dict(sch,type='round',head_values=[rt['head_b_base'] if h==2 else sch['test_bits'],sch['test_bits']],result_bits=sch['test_bits'],status_raw=0,near_architectural=arch,far_architectural_words=[arch]*8,code_base=rt['code_base'],code_matches_plan=True),'cold actual head/marker original');packets.audit_envelope([*block['warm'],z],idx);formal.append(z);warm.extend(block['warm'])
  else:
   packets.validate_rejection(block['rejected'],idx)
   if block['warm']:packets.audit_envelope(block['warm'],idx)
 return dict(condition=c['name'],args=c['args'],status='complete',config=rr[0],programs=rr[1:5],runtime=rt,samples=formal,warmup_windows=warm,invalid_packets=parsed['invalid'],final=rr[-1])
def analyze(rows):
 _require(len(rows)==16,'cold full16 processes');points=[];by={};long=[];cache=[];markers=[]
 for row,c in zip(rows,conditions()):
  _require(row['condition']==c['name'] and row['status']=='complete','cold condition');x=copy.deepcopy(row);x['config'].update(chain=row['config']['heads'],gap=0,filler='cold-head');v=admission.classify_process(x,c)
  if row['config']['palette']=='cache':v['supply_qualified']=None;v['classification']='CACHE_PROFILE_NO_ICACHE_GATE';v['cache_fields']='0x3-L1D/0x17-L2D'
  elif row['config']['state']=='cold':markers.append(v['marker_observable'] and v['supply_qualified'])
  points.append(v);by[c['name']]=row
 contrasts=[]
 for e in range(2):
  for h in (1,2):
   for p in PALETTES:
    hot=by[f'e{e}-h{h}-{p}-hot'];cold=by[f'e{e}-h{h}-{p}-cold'];hh={(z['trial'],z['control'],z['fence'],z['marker']):z for z in hot['samples']};cc={(z['trial'],z['control'],z['fence'],z['marker']):z for z in cold['samples']};diff={};gates={}
    for f in ('pre','post'):
     for m in ('nop','taps'):
      tt=sorted(t for t in range(32) if (t,'architect',f,m) in hh and (t,'architect',f,m) in cc);_require(len(tt)>=30,'cold paired crossprocess coverage');vv=[[cc[t,'architect',f,m]['counts'][j]-hh[t,'architect',f,m]['counts'][j] for t in tt] for j in range(6)];key=f+'-'+m;diff[key]=dict(trials=tt,counts=vv,medians=[st.median(v) for v in vv]);gates[key+'-long']=st.median(vv[0])>=(64 if h==1 else 96)
      if p=='cache':gates[key+'-cache']=all(.75*h<=st.mean(vv[j])<=1.25*h for j in (4,5))
    long.append(all(v for k,v in gates.items() if k.endswith('-long')))
    if p=='cache':cache.append(all(v for k,v in gates.items() if k.endswith('-cache')))
    contrasts.append(dict(epoch=e,heads=h,palette=p,cold_minus_hot=diff,gates=gates))
 return dict(mode=MODE,status='COLD_HEAD_MARKER_QUALIFIED' if all(markers) and all(long) and all(cache) else 'COLD_HEAD_NOT_QUALIFIED',attempted_packets=4096,windows=sum(len(r['samples']) for r in rows),owned_warm_windows=sum(len(r['warmup_windows']) for r in rows),invalid_packets=sum(len(r['invalid_packets']) for r in rows),processes=points,contrasts=contrasts,physical_capacity_certified=False)
