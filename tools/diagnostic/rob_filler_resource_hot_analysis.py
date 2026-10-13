"""Final-RX warm ownership is audited; formal-window decisions stay v1 frozen."""
import copy
from tools.diagnostic import rob_filler_resource_analysis as base
from tools.diagnostic.rob_direct_fenced_analysis import check_roi
from tools.diagnostic.analyze_cold_pair import _require,_same
MODE='rob-filler-resource-hot';EVIDENCE='docs/reviews/evidence/2026-10-14-rob-filler-resource-hot'
PROTOCOL='docs/design/2026-10-14-rob-filler-resource-hot.md';CONSUMER='tools/diagnostic/rob_filler_resource_hot_analysis.py';DRIVER='tools/diagnostic/run_sm8650_rob_filler_resource_hot.py'
def expected(n,f,idx=base.register.DEFAULT_INDICES):
 p=base.expected(n,f,idx);p[0].update(probe=MODE,final_RX_owned_warm_calls=4,warm_protocol='post-RX-owned-ROI');return p
def conditions():return base.conditions()
def plans():return {f'{n}-{f}':expected(n,f) for n in (32,64) for f in (0,4,8,12)}
def audit_process(rr,c,registered):
 _require(_same(registered,plans()),'hot actual native plans');n=int(c['args'][2]);f=int(c['args'][4]);_require(type(rr)is list and len(rr)>=2 and _same(rr[0],expected(n,f)[0]),'hot config')
 if rr[-1].get('type')=='failure':return dict(condition=c['name'],args=c['args'],status='TECHNICAL_FAILURE',failure=rr[-1]['failure'])
 _require(len(rr)==1287,'hot all warm and formal windows');runtime=rr[5];idx=base.register.indices(runtime.get('counter_indices'));want=expected(n,f,idx);_require(_same(rr[:5],want[:5]),'hot runtime native words');formal=[];warm=[]
 for i,s in enumerate(want[5:]):
  block=rr[6+5*i:6+5*(i+1)];_require(len(block)==5,'hot block')
  for ordinal,z in enumerate(block[:4]):
   fields=dict(type='warm-roi',trial=s['trial'],position=s['position'],ordinal=ordinal,control=s['control'],unit=s['unit'],input_bits=s['input_bits'],result_bits=s['input_bits'],checksum=n*0x12345678,reserved_output=(runtime['near_base']+runtime['far_base'])&((1<<64)-1) if s['unit']=='live' and f else 0)
   _require(all(_same(z.get(k),v) for k,v in fields.items()),'hot warm ordinal/originals');check_roi(z);_require([v['index'] for v in z['roi_before']]==idx,'hot current warm indices');_require(type(z.get('enabled'))is int and z['enabled']>0 and z.get('running')==z['enabled'],'hot warm noMUX');warm.append(z)
  formal.append(block[4])
 cfg=copy.deepcopy(rr[0]);cfg.update(probe=base.MODE);cfg.pop('final_RX_owned_warm_calls');cfg.pop('warm_protocol');row=base.audit_process([cfg,*rr[1:6],*formal,rr[-1]],c,{f'{n}-{f}':base.expected(n,f) for n in (32,64) for f in (0,4,8,12)});row['warmup_windows']=warm;row['config']=rr[0];return row
def analyze(rows):
 v=base.analyze(rows);v['mode']=MODE;v['owned_warm_windows']=16384;v['warm_protocol']='post-RX-owned-ROI';return v
