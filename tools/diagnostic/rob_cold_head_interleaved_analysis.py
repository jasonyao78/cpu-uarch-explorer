"""同映射hot/cold配对与offset反证；锚点 cold-head-interleaved v2.0，绝不认证ROB slot。"""
import copy, statistics as st
from tools.diagnostic import rob_cold_head_analysis as old
from tools.diagnostic import rob_admission_window_analysis as admission
from tools.diagnostic import owned_roi_packets as packets
from tools.diagnostic.analyze_cold_pair import _require, _same, _fields
MODE='rob-cold-head-interleaved';EVIDENCE='docs/reviews/evidence/2026-10-14-rob-cold-head-interleaved'
PROTOCOL='docs/design/2026-10-14-rob-cold-head-interleaved.md';CONSUMER='tools/diagnostic/rob_cold_head_interleaved_analysis.py';DRIVER='tools/diagnostic/run_sm8650_rob_cold_head_interleaved.py'
PALETTES=old.PALETTES

def expected(heads,palette,offset,idx=admission.register.DEFAULT_INDICES):
 """返回固定ISA及512state原生计划；只允许预注册offset。"""
 _require(offset in (0,1024),'interleaved registered offset')
 base=old.expected(heads,palette,'hot',idx);cfg=base[0];cfg.pop('state');cfg.update(version=6,probe=MODE,head_offset=offset,windows=512)
 schedule=[]
 for t in range(32):
  for pos in range(16):
   i=(t+pos)%16;i=15-i if (t//8)%2 else i;role=i%8;control=role//4
   schedule.append(dict(type='schedule',trial=t,position=pos,state='cold' if i>=8 else 'hot',control=('architect','speculate')[control],marker='taps' if role%2 else 'nop',fence='pre' if role%4<2 else 'post',train_bits=0,test_bits=control))
 return [*base[:5],*schedule]

def plans():
 """静态注册八组合；actual own index每process另外逐词核验。"""
 return {f'{h}-{p}-{o}':expected(h,p,o) for h in (1,2) for p in PALETTES for o in (0,1024)}

def conditions():
 """两fresh epoch逆序；16process不重试不挑点。"""
 grid=[(h,p,o) for h in (1,2) for p in PALETTES for o in (0,1024)]
 return [dict(name=f'e{e}-h{h}-{p}-o{o}',args=['--run','--heads',str(h),'--palette',p,'--head-offset',str(o)]) for e in range(2) for h,p,o in (grid if e==0 else reversed(grid))]

def audit_process(rr,c,registered):
 """核验真实头地址/内容链/PFN、ISA、state、每窗PMU算术与同FD包络；失败保留空metrics。"""
 _require(_same(registered,plans()),'interleaved native registered plans');h=int(c['args'][2]);p=c['args'][4];off=int(c['args'][6])
 _require(type(rr)is list and len(rr)>=2 and _same(rr[0],expected(h,p,off)[0]),'interleaved config')
 if rr[-1].get('type')=='failure':
  _require(rr[-1].get('metrics')=={} and type(rr[-1].get('failure'))is dict,'interleaved failure')
  return dict(condition=c['name'],args=c['args'],status='TECHNICAL_FAILURE',failure=rr[-1]['failure'])
 idx=admission.register.indices(rr[5].get('counter_indices'));want=expected(h,p,off,idx);_require(_same(rr[:5],want[:5]),'interleaved actual words');rt=packets.runtime(rr,idx)
 before=rt.get('head_pagemap_before');after=rr[-1].get('head_pagemap_after');_require(type(before)is list and type(after)is list and len(before)==len(after)==2,'interleaved head backing')
 def pfn(v):
  _require(type(v)is int and 0<=v<1<<64 and v>>63 and not(v&(1<<62)) and v&((1<<55)-1),'interleaved visible PFN');return v&((1<<55)-1)
 _require([pfn(v) for v in before]==[pfn(v) for v in after] and len(set(pfn(v) for v in before+rt['pagemap_before']))==6,'interleaved stable private maps')
 _require(type(rt.get('head_offset'))is int and rt['head_offset']==off,'interleaved actual requested offset')
 for name in ('head_a','head_b'):
  base=rt.get(name+'_map_base');addr=rt.get(name+'_base');_require(type(base)is int and base>0 and base%4096==0 and type(addr)is int and addr==base+off,'interleaved realized head address')
 _require(len({rt[n+'_base'] for n in ('code','near','far','output')}|{rt['head_a_map_base'],rt['head_b_map_base']})==6,'interleaved distinct actual mappings')
 _require(_same(rt.get('head_initial_values'),[rt['head_b_base'] if h==2 else 0,0]),'interleaved initial realized dependency')
 parsed=packets.decode(rr[6:-1],want[5:]);packets.final_counts(rr[-1],parsed);formal=[];warm=[]
 for block in parsed['valid']+parsed['invalid']:
  sch=block['schedule'];arch=0x12345678 if sch['marker']=='taps' else 0
  for ordinal,z in enumerate(block['warm']):
   _fields(z,dict(type='warm-roi',state=sch['state'],trial=sch['trial'],position=sch['position'],ordinal=ordinal,control=sch['control'],marker=sch['marker'],fence=sch['fence'],train_bits=0,result_bits=0,status_raw=0,near_architectural=arch,far_architectural_words=[arch]*8),'interleaved hot training original')
  if 'sample' in block:
   z=block['sample'];arch=0x12345678 if sch['control']=='architect' and sch['marker']=='taps' else 0
   _fields(z,dict(sch,type='round',head_values=[rt['head_b_base'] if h==2 else sch['test_bits'],sch['test_bits']],result_bits=sch['test_bits'],status_raw=0,near_architectural=arch,far_architectural_words=[arch]*8,code_base=rt['code_base'],code_matches_plan=True),'interleaved realized head/marker original')
   packets.audit_envelope([*block['warm'],z],idx);formal.append(z);warm.extend(block['warm'])
  else:
   packets.validate_rejection(block['rejected'],idx)
   if block['warm']:packets.audit_envelope(block['warm'],idx)
 return dict(condition=c['name'],args=c['args'],status='complete',config=rr[0],programs=rr[1:5],runtime=rt,samples=formal,warmup_windows=warm,invalid_packets=parsed['invalid'],final=rr[-1])

def analyze(rows):
 """保留两offset全部原门，1024主资格在采样前指定；UNKNOWN不变零。"""
 _require(len(rows)==16,'interleaved full16 processes');points=[];contrasts=[];primary=[]
 for row,c in zip(rows,conditions()):
  _require(row['condition']==c['name'] and row['status']=='complete','interleaved condition');h=row['config']['heads'];p=row['config']['palette'];off=row['config']['head_offset'];local=[]
  for state in ('hot','cold'):
   x=copy.deepcopy(row);x['samples']=[z for z in row['samples'] if z['state']==state];x['invalid_packets']=[z for z in row['invalid_packets'] if z['schedule']['state']==state];x['condition']=c['name']+'-'+state;x['config'].update(chain=h,gap=0,filler='cold-head');v=admission.classify_process(x,dict(c,name=x['condition']))
   v.update(state=state,head_offset=off,heads=h,palette=p)
   if p=='cache':
    v['supply_qualified']=None;v['classification']='CACHE_PROFILE_NO_ICACHE_GATE';v['cache_fields']='0x3-L1D/0x17-L2D';v['deltas']={role:{'0x3' if event=='0x22' else '0x17' if event=='0x1' else event:values for event,values in counts.items()} for role,counts in v['deltas'].items()}
   points.append(v);local.append(v)
  cells={(z['trial'],z['state'],z['control'],z['fence'],z['marker']):z for z in row['samples']};_require(len(cells)==len(row['samples']),'interleaved state-sensitive unique key');diff={};gates={}
  for f in ('pre','post'):
   for m in ('nop','taps'):
    tt=packets.paired_trials(cells,('hot','architect',f,m),('cold','architect',f,m));vv=[[cells[t,'cold','architect',f,m]['counts'][j]-cells[t,'hot','architect',f,m]['counts'][j] for t in tt] for j in range(6)];key=f+'-'+m;diff[key]=dict(trials=tt,counts=vv,medians=[st.median(v) for v in vv],means=[st.mean(v) for v in vv]);gates[key+'-long']=st.median(vv[0])>=(64 if h==1 else 96)
    if p=='cache':gates[key+'-cache']=all(.75*h<=st.mean(vv[j])<=1.25*h for j in (4,5))
  gates['all_marker_calibration']=all(all(v['gates'].values()) for v in local);gates['cold_marker_observable']=local[1]['marker_observable']
  if p=='issue':gates['strict_supply']=all(v['supply_qualified'] for v in local)
  accepted=all(gates.values());contrasts.append(dict(name=c['name'],epoch=int(c['name'][1]),heads=h,palette=p,head_offset=off,cold_minus_hot=diff,gates=gates,qualified=accepted))
  if off==1024:primary.append(accepted)
 return dict(mode=MODE,status='INTERLEAVED_COLD_HEAD_PRIMARY_QUALIFIED' if all(primary) else 'INTERLEAVED_COLD_HEAD_NOT_QUALIFIED',attempted_packets=8192,windows=sum(len(r['samples']) for r in rows),owned_warm_windows=sum(len(r['warmup_windows']) for r in rows),invalid_packets=sum(len(r['invalid_packets']) for r in rows),processes=points,contrasts=contrasts,physical_capacity_certified=False,ROB_allocation_units_certified=False)
