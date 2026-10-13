"""Strict own direct counter metadata, wrap, envelope and known-work controls.

Long-work qualification only; never physical ROB entries or short-window proof.
"""
import statistics
from tools.diagnostic.analyze_cold_pair import _same,_require
EVIDENCE='docs/reviews/evidence/2026-10-13-pmu-own-counter'
PROTOCOL='docs/design/2026-10-13-pmu-own-direct-counter.md'
CONSUMER='tools/diagnostic/pmu_own_counter_analysis.py'
DRIVER='tools/diagnostic/run_sm8650_pmu_own_counter.py'
MASK=(1<<64)-1
def expected(epoch):return dict(probe='pmu-own-counter',version=1,epoch=epoch,events=[17,8,112,113],config1=3,iterations=8192,rounds=8,roles=['nop','load','store'],cpu=7,pmu_type=8,owned_direct_read=True,global_policy_mutation=False)
def direct(v):
 _require(type(v)is dict and v.get('cap')is True,'direct capability')
 for key in ('sequence_before','sequence_after','index','width','offset','hardware','total'):_require(type(v.get(key))is int and 0<=v[key]<=MASK,'direct unsigned '+key)
 _require(1<=v['index']<=32 and v['width']==64 and v['sequence_before']==v['sequence_after'] and not(v['sequence_before']&1),'direct eligibility')
 _require(v['total']==((v['offset']+v['hardware'])&MASK),'direct offset/raw total');return v['total']
def four(v):
 _require(type(v)is list and len(v)==4,'direct four');out=[direct(x) for x in v];_require(len({x['index'] for x in v})==4,'unique own counter mapping');return out

def kernel(v):
 _require(type(v)is list and len(v)==4 and all(type(x)is int and 0<=x<=MASK for x in v),'kernel four unsigned');return v

def audit_process(rr,p):
 _require(type(rr)is list and len(rr)>=2 and _same(rr[0],p),'exact direct plan')
 if rr[-1].get('type')=='failure':
  _require(rr[-1].get('metrics')=={} and rr[-1].get('fds_closed')is True and type(rr[-1].get('failure'))is dict,'direct structured failure');return dict(status='OWN_DIRECT_COUNTER_NOT_QUALIFIED',failure=rr[-1]['failure'],rows=[],physical_capacity_certified=False)
 _require(len(rr)==27 and _same(rr[1],dict(type='policy',actual=1,read_only=True)) and _same(rr[-1],dict(type='final',fds_closed=True,global_policy_mutation=False,owned_direct_read=True)),'direct full coverage/final');rows=[]
 for ordinal,w in enumerate(rr[2:-1]):
  role=2-ordinal%3 if p['epoch']==1 else ordinal%3
  _require(all(_same(w.get(k),v) for k,v in dict(type='window',round=ordinal//3,role=role,cpu=7).items()),'direct window identity')
  _require(type(w.get('enabled'))is int and w['enabled']>0 and _same(w.get('running'),w['enabled']),'direct noMUX');a=kernel(w.get('kernel_before'));b=kernel(w.get('kernel_after'));_require(all(y>=x for x,y in zip(a,b)),'kernel regression');fd=[y-x for x,y in zip(a,b)];pre=w.get('direct_before');post=w.get('direct_after');a=four(pre);b=four(post);_require(all(lo<=v<=hi and lo<=z<=hi for lo,hi,v,z in zip(w['kernel_before'],w['kernel_after'],a,b)),'absolute direct-to-FD counter identity')
  _require(all(x[k]==y[k] for x,y in zip(pre,post) for k in ('sequence_before','sequence_after','index','offset')),'metadata changed in window');dd=[(y-x)&MASK for x,y in zip(a,b)];_require(all(0<=x<=y for x,y in zip(dd,fd)),'direct not contained in FD');wrapper=[y-x for x,y in zip(dd,fd)];_require(dd[0]>0 and dd[1]>0 and wrapper[1]<=4096 and wrapper[2]<=512 and wrapper[3]<=512,'direct wrapper envelope');rows.append(dict(round=w['round'],role=role,direct=dd,kernel=fd,wrapper=wrapper))
 med={role:[statistics.median(x['direct'][j] for x in rows if x['role']==role) for j in range(4)] for role in range(3)};load=[med[1][j]-med[0][j] for j in range(4)];store=[med[2][j]-med[0][j] for j in range(4)];checks=dict(load_signal=abs(load[2]-8192)<=82,store_signal=abs(store[3]-8192)<=82,load_cross=abs(load[3])<=128,store_cross=abs(store[2])<=128,load_IR=abs(load[1])<=128,store_IR=abs(store[1])<=128)
 return dict(status='OWN_DIRECT_COUNTER_QUALIFIED' if all(checks.values()) else 'OWN_DIRECT_COUNTER_NOT_QUALIFIED',rows=rows,checks=checks,load_minus_nop=load,store_minus_nop=store,physical_capacity_certified=False,short_window_precision_certified=False)
