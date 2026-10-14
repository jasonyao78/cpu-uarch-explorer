"""固定/role/packet实际branch PC与wrong-direction机会反证；锚点 cold-head-branch-sites v1.0，绝不认证ROB slot。"""
import copy, statistics as st
from tools.diagnostic import rob_cold_head_interleaved_analysis as old
from tools.diagnostic import rob_admission_window_analysis as admission
from tools.diagnostic import owned_roi_packets as packets
from tools.diagnostic.analyze_cold_pair import _require, _same, _fields
MODE='rob-cold-head-branch-sites';EVIDENCE='docs/reviews/evidence/2026-10-14-rob-cold-head-branch-sites'
PROTOCOL='docs/design/2026-10-14-rob-cold-head-branch-sites.md';CONSUMER='tools/diagnostic/rob_cold_head_branch_sites_analysis.py';DRIVER='tools/diagnostic/run_sm8650_rob_cold_head_branch_sites.py'
PALETTES=old.PALETTES

LAYOUTS=('fixed','trial-role','packet')
def expected(heads,palette,offset,layout,idx=admission.register.DEFAULT_INDICES):
 """固定ISA与actual slot/branch偏移；只允许issue/1024/三布局。"""
 _require(palette=='issue' and offset==1024 and layout in LAYOUTS,'sites frozen parameters')
 rr=old.expected(heads,palette,offset,idx);rr[0].update(version=7,probe=MODE,branch_layout=layout)
 for z in rr[5:]:
  role=4*int(z['control']=='speculate')+2*int(z['fence']=='post')+int(z['marker']=='taps');i=role+8*int(z['state']=='cold')
  off=0 if layout=='fixed' else 8*(z['trial']*8+role) if layout=='trial-role' else 4*(z['trial']*16+i)
  z.update(code_offset=off,branch_offset=off+4*(33+heads))
 return rr

def plans():
 """六组合实际计划；actual own index逐process重新绑定。"""
 return {f'{h}-{l}':expected(h,'issue',1024,l) for h in (1,2) for l in LAYOUTS}

def conditions():
 """两个fresh epoch的12固定process；不同PC控制全部保留。"""
 grid=[(h,l) for h in (1,2) for l in LAYOUTS]
 return [dict(name=f'e{e}-h{h}-{l}',args=['--run','--heads',str(h),'--palette','issue','--head-offset','1024','--branch-layout',l]) for e in range(2) for h,l in (grid if e==0 else reversed(grid))]

def audit_process(rr,c,registered,*,expected_recipe=None,recipe_registry=None):
 """核验真实地址/ISA/current FD；可信consumer可传冻结recipe，默认issue原合同不变。"""
 recipe=expected if expected_recipe is None else expected_recipe;registry=plans if recipe_registry is None else recipe_registry
 _require(_same(registered,registry()),'sites native registered plans');h=int(c['args'][2]);p=c['args'][4];off=int(c['args'][6]);layout=c['args'][8]
 _require(type(rr)is list and len(rr)>=2 and _same(rr[0],recipe(h,p,off,layout)[0]),'interleaved config')
 if rr[-1].get('type')=='failure':
  _require(rr[-1].get('metrics')=={} and type(rr[-1].get('failure'))is dict,'interleaved failure')
  return dict(condition=c['name'],args=c['args'],status='TECHNICAL_FAILURE',failure=rr[-1]['failure'])
 idx=admission.register.indices(rr[5].get('counter_indices'));want=recipe(h,p,off,layout,idx);_require(_same(rr[:5],want[:5]),'interleaved actual words');rt=packets.runtime(rr,idx)
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
  sch=block['schedule'];location=dict(code_offset=sch['code_offset'],branch_offset=sch['branch_offset'],code_base=rt['code_base']+sch['code_offset'],branch_pc=rt['code_base']+sch['branch_offset']);arch=0x12345678 if sch['marker']=='taps' else 0
  for ordinal,z in enumerate(block['warm']):
   _fields(z,dict(location,type='warm-roi',state=sch['state'],trial=sch['trial'],position=sch['position'],ordinal=ordinal,control=sch['control'],marker=sch['marker'],fence=sch['fence'],train_bits=0,result_bits=0,status_raw=0,near_architectural=arch,far_architectural_words=[arch]*8),'interleaved hot training original')
  if 'sample' in block:
   z=block['sample'];arch=0x12345678 if sch['control']=='architect' and sch['marker']=='taps' else 0
   _fields(z,dict(sch,type='round',head_values=[rt['head_b_base'] if h==2 else sch['test_bits'],sch['test_bits']],result_bits=sch['test_bits'],status_raw=0,near_architectural=arch,far_architectural_words=[arch]*8,code_base=location['code_base'],branch_pc=location['branch_pc'],code_matches_plan=True),'interleaved realized head/marker original')
   packets.audit_envelope([*block['warm'],z],idx);formal.append(z);warm.extend(block['warm'])
  else:
   _fields(block['rejected'],location,'sites actual rejected PC');_fields(block['invalid'],location,'sites actual invalid PC');packets.validate_rejection(block['rejected'],idx)
   if block['warm']:packets.audit_envelope(block['warm'],idx)
 return dict(condition=c['name'],args=c['args'],status='complete',config=rr[0],programs=rr[1:5],runtime=rt,samples=formal,warmup_windows=warm,invalid_packets=parsed['invalid'],final=rr[-1])

def analyze(rows):
 """保留三个PC干预全部原门，packet主资格在采样前指定；UNKNOWN不变零。"""
 _require(len(rows)==12,'sites full12 processes');points=[];contrasts=[];primary=[]
 for row,c in zip(rows,conditions()):
  _require(row['condition']==c['name'] and row['status']=='complete','interleaved condition');h=row['config']['heads'];p=row['config']['palette'];off=row['config']['head_offset'];layout=row['config']['branch_layout'];local=[]
  for state in ('hot','cold'):
   x=copy.deepcopy(row);x['samples']=[z for z in row['samples'] if z['state']==state];x['invalid_packets']=[z for z in row['invalid_packets'] if z['schedule']['state']==state];x['condition']=c['name']+'-'+state;x['config'].update(chain=h,gap=0,filler='cold-head');v=admission.classify_process(x,dict(c,name=x['condition']))
   v.update(state=state,head_offset=off,heads=h,palette=p,branch_layout=layout)
   points.append(v);local.append(v)
  cells={(z['trial'],z['state'],z['control'],z['fence'],z['marker']):z for z in row['samples']};_require(len(cells)==len(row['samples']),'interleaved state-sensitive unique key');diff={};gates={}
  for f in ('pre','post'):
   for m in ('nop','taps'):
    tt=packets.paired_trials(cells,('hot','architect',f,m),('cold','architect',f,m));vv=[[cells[t,'cold','architect',f,m]['counts'][j]-cells[t,'hot','architect',f,m]['counts'][j] for t in tt] for j in range(6)];key=f+'-'+m;diff[key]=dict(trials=tt,counts=vv,medians=[st.median(v) for v in vv],means=[st.mean(v) for v in vv]);gates[key+'-long']=st.median(vv[0])>=(64 if h==1 else 96)
  gates['all_marker_calibration']=all(all(v['gates'].values()) for v in local);gates['cold_marker_observable']=local[1]['marker_observable']
  if p=='issue':gates['strict_supply']=all(v['supply_qualified'] for v in local)
  cold=[z for z in row['samples'] if z['state']=='cold' and z['control']=='speculate' and z['fence']=='post' and z['marker']=='taps'];negative=[z for z in row['samples'] if z['state']=='cold' and z['control']=='architect' and z['fence']=='post' and z['marker']=='taps']
  association=sum((z['counts'][4]==0 and z['counts'][2]-h==0 and z['counts'][3]-2==0) or (z['counts'][4]==1 and z['counts'][2]-h>=4 and z['counts'][3]-2>=4) for z in cold)
  strong=dict(near24=len(local[1]['eligible_trials'])>=24,wrong_direction24=sum(z['counts'][4]==1 for z in cold)>=24,architect_negative29=sum(z['counts'][4]==0 for z in negative)>=29,joint29=association>=29)
  if layout=='packet':gates.update(strong)
  accepted=all(gates.values());contrasts.append(dict(name=c['name'],epoch=int(c['name'][1]),heads=h,palette=p,head_offset=off,branch_layout=layout,strong_opportunity_gates=strong,wrong_direction_windows=sum(z['counts'][4]==1 for z in cold),joint_windows=association,cold_minus_hot=diff,gates=gates,qualified=accepted))
  if layout=='packet':primary.append(accepted)
 return dict(mode=MODE,status='BRANCH_SITES_PRIMARY_QUALIFIED' if all(primary) else 'BRANCH_SITES_NOT_QUALIFIED',attempted_packets=6144,windows=sum(len(r['samples']) for r in rows),owned_warm_windows=sum(len(r['warmup_windows']) for r in rows),invalid_packets=sum(len(r['invalid_packets']) for r in rows),processes=points,contrasts=contrasts,physical_capacity_certified=False,ROB_allocation_units_certified=False)
