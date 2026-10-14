"""当前packet-PC的实际cache剂量资格；锚点 packet-cache v1.0，不外推固定PC。"""
import copy,statistics as st
from tools.diagnostic import rob_cold_head_interleaved_analysis as inter
from tools.diagnostic import rob_cold_head_branch_sites_analysis as sites
from tools.diagnostic import rob_admission_window_analysis as admission
from tools.diagnostic import owned_roi_packets as packets
from tools.diagnostic.analyze_cold_pair import _require,_same
MODE='rob-cold-head-packet-cache';EVIDENCE='docs/reviews/evidence/2026-10-14-rob-cold-head-packet-cache'
PROTOCOL='docs/design/2026-10-14-rob-cold-head-packet-cache.md';CONSUMER='tools/diagnostic/rob_cold_head_packet_cache_analysis.py';DRIVER='tools/diagnostic/run_sm8650_rob_cold_head_packet_cache.py'
LAYOUTS=('packet',)
def expected(h,palette,offset,layout,idx=admission.register.DEFAULT_INDICES):
 """只注册actual cache palette/packet/1024，共享唯一ROI源的实际位置配方。"""
 _require(palette=='cache' and offset==1024 and layout=='packet','packet cache frozen parameters')
 rr=inter.expected(h,palette,offset,idx);rr[0].update(version=7,probe=MODE,branch_layout=layout)
 for z in rr[5:]:
  role=4*int(z['control']=='speculate')+2*int(z['fence']=='post')+int(z['marker']=='taps');off=4*(z['trial']*16+role+8*int(z['state']=='cold'));z.update(code_offset=off,branch_offset=off+4*(33+h))
 return rr

def plans():
 """两head组合；actual own index每FD新比对。"""
 return {f'{h}-packet':expected(h,'cache',1024,'packet') for h in (1,2)}

def conditions():
 """四fresh process，epoch1逆序；无scan/补样。"""
 return [dict(name=f'e{e}-h{h}-packet',args=['--run','--heads',str(h),'--palette','cache','--head-offset','1024','--branch-layout','packet']) for e in range(2) for h in ((1,2) if e==0 else (2,1))]

def audit_process(rr,c,registered):
 """用本consumer冻结recipe审计原始实际PC/ISA/FD，不改原raw。"""
 return sites.audit_process(rr,c,registered,expected_recipe=expected,recipe_registry=plans)

def analyze(rows):
 """四配置全部原marker/24机会/long/cache剂量门才通过；本palette不审I-cache/0x22。"""
 _require(len(rows)==4,'packet cache full4');points=[];contrasts=[];accepted=[]
 for row,c in zip(rows,conditions()):
  _require(row['condition']==c['name'] and row['status']=='complete','packet cache identity');h=row['config']['heads'];local=[]
  for state in ('hot','cold'):
   x=copy.deepcopy(row);x['samples']=[z for z in row['samples'] if z['state']==state];x['invalid_packets']=[z for z in row['invalid_packets'] if z['schedule']['state']==state];x['condition']=c['name']+'-'+state;x['config'].update(chain=h,gap=0,filler='cold-head')
   v=admission.classify_process(x,dict(c,name=x['condition']));v.update(state=state,head_offset=1024,heads=h,palette='cache',branch_layout='packet',supply_qualified=None,classification='CACHE_PROFILE_NO_ICACHE_GATE',cache_fields='0x3-L1D/0x17-L2D');v['deltas']={role:{'0x3' if event=='0x22' else '0x17' if event=='0x1' else event:values for event,values in counts.items()} for role,counts in v['deltas'].items()};points.append(v);local.append(v)
  cells={(z['trial'],z['state'],z['control'],z['fence'],z['marker']):z for z in row['samples']};_require(len(cells)==len(row['samples']),'cache state-sensitive unique key');diff={};gates={}
  for f in ('pre','post'):
   for m in ('nop','taps'):
    tt=packets.paired_trials(cells,('hot','architect',f,m),('cold','architect',f,m));vv=[[cells[t,'cold','architect',f,m]['counts'][j]-cells[t,'hot','architect',f,m]['counts'][j] for t in tt] for j in range(6)];key=f+'-'+m;diff[key]=dict(trials=tt,counts=vv,medians=[st.median(v) for v in vv],means=[st.mean(v) for v in vv]);gates[key+'-long']=st.median(vv[0])>=(64 if h==1 else 96);gates[key+'-cache']=all(.75*h<=st.mean(vv[j])<=1.25*h for j in (4,5))
  gates.update(all_marker_calibration=all(all(v['gates'].values()) for v in local),cold_marker_observable=local[1]['marker_observable'],near24=len(local[1]['eligible_trials'])>=24);ok=all(gates.values());accepted.append(ok);contrasts.append(dict(name=c['name'],epoch=int(c['name'][1]),heads=h,palette='cache',head_offset=1024,branch_layout='packet',cold_minus_hot=diff,gates=gates,qualified=ok))
 return dict(mode=MODE,status='PACKET_CACHE_PRIMARY_QUALIFIED' if all(accepted) else 'PACKET_CACHE_NOT_QUALIFIED',attempted_packets=2048,windows=sum(len(r['samples']) for r in rows),owned_warm_windows=sum(len(r['warmup_windows']) for r in rows),invalid_packets=sum(len(r['invalid_packets']) for r in rows),processes=points,contrasts=contrasts,physical_capacity_certified=False,ROB_allocation_units_certified=False)
