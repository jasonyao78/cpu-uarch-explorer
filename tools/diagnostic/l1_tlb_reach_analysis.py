"""Typed producer-to-criterion audit; no cache/cycle proxy promoted to capacity.

Contract docs/design/2026-10-13-l1-tlb-reach.md. Full mapping, layouts, coverage
and cumulative PMU values are verified before any onset classification.
"""
import statistics
from tools.diagnostic.analyze_cold_pair import _same,_require
I_N=[32,40,44,48,52,56,64,96,112,120,124,128,132,144,160,192]
D_N=[32,64,80,88,92,96,100,104,112,128,160,192]
EVIDENCE='docs/reviews/evidence/2026-10-13-l1-tlb-reach'
PROTOCOL='docs/design/2026-10-13-l1-tlb-reach.md'
CONSUMER='tools/diagnostic/l1_tlb_reach_analysis.py'
DRIVER='tools/diagnostic/run_sm8650_l1_tlb_reach.py'
def expected(mode,epoch,phase):
 _require(mode in ('i','d') and type(epoch)is int and epoch in range(3) and phase in ('qualification','scan'),'registered inputs')
 return dict(probe='l1-tlb-reach',version=1,mode=mode,epoch=epoch,phase=phase,cpu=7,pmu_type=8,events=[17,8,2,53,1,34] if mode=='i' else [17,8,5,52,3,1],nodes=[32] if phase=='qualification' else (I_N if mode=='i' else D_N),strides=[5,17],rounds=3,empty_each_side=3,target_hops=1000000,global_policy_mutation=False,backing_pages=192,seed=137,jit_slots_bytes=[0,16,32,48])
def counters(v):
 _require(type(v)is list and len(v)==6 and all(type(x)is int and 0<=x<1<<64 for x in v),'strict six counters');return v

def words(base,stride,role,order):
 def address(i):return base+i*stride*4096+role*16+((i&63)*64 if role&1 else 0)
 def b(a,z):
  _require((z-a)%4==0 and -(1<<27)<=z-a<1<<27,'direct branch range');return 0x14000000|(((z-a)//4)&0x3ffffff)
 result=[]
 for k,i in enumerate(order):
  a=address(i);result.append([b(a,address(order[k+1])),0,0,0] if k+1<len(order) else [0xf1000400,0x54000040,b(a+8,address(order[0])),0xd65f03c0])
 return result

def trajectory(n,epoch):
 o=list(range(n));s=137
 for i in range(n-1,0,-1):s=(1664525*s+1013904223)&0xffffffff;j=s%(i+1);o[i],o[j]=o[j],o[i]
 return list(reversed(o)) if epoch==1 else o

def onset(points):
 q=sorted(points);s=['below' if v<=.01 else 'above' if v>=.1 else 'ambiguous' for _,v in q]
 if 'ambiguous' in s:return dict(status='ambiguous',interval=None)
 if not q or 'above' not in s:return dict(status='right-censored',interval=None)
 if s[0]=='above':return dict(status='left-censored',interval=None)
 i=s.index('above')
 if 'below' in s[i:]:return dict(status='nonmonotone',interval=None)
 if len(s)-i<2:return dict(status='right-censored',interval=None)
 return dict(status='localized',interval=[q[i-1][0],q[i][0]])

def audit_process(rr,p):
 _require(type(rr)is list and len(rr)>=3 and _same(rr[0],p),'producer exact plan')
 _require(_same(rr[-1],dict(type='final',fds_closed=True,mapping_unchanged=True,code_checked=True,global_policy_mutation=False)),'final cleanup/mapping')
 m=rr[1];_require(m.get('type')=='mapping' and type(m.get('pfns'))is list and len(m['pfns'])==192 and len(set(m['pfns']))==192 and all(type(x)is int and 0<x<1<<55 for x in m['pfns']),'actual own PFNs');bases=m.get('alias_bases');_require(type(bases)is list and len(bases)==2 and len(set(bases))==2 and all(type(b)is int and b>0 and b%4096==0 for b in bases),'actual aliases')
 nodes=p['nodes'];iteration=list(reversed(nodes)) if p['epoch']==1 else nodes;_require(len(rr)==3+19*len(nodes),'exact layout/window coverage');rows=[]
 for ni,n in enumerate(iteration):
  layout=rr[2+19*ni];h=(1000000//n)*n;cy=h//n;order=trajectory(n,p['epoch']);_require(layout.get('type')=='layout' and _same(layout.get('nodes'),n) and _same(layout.get('hops'),h) and _same(layout.get('cycles'),cy) and _same(layout.get('order'),order),'actual complete circuit')
  _require(_same(layout.get('words'),[words(bases[role//2],p['strides'][role//2],role,order) for role in range(4)] if p['mode']=='i' else []),'actual JIT words')
  ww=rr[3+19*ni:21+19*ni];delta=[]
  for ordinal,w in enumerate(ww):
   role=-1 if ordinal<3 or ordinal>=15 else (3-(ordinal-3)%4 if p['epoch']==1 else (ordinal-3)%4);round_=0 if role==-1 else (ordinal-3)//4
   _require(all(_same(w.get(k),v) for k,v in dict(type='window',nodes=n,ordinal=ordinal,role=role,round=round_,cpu=7).items()),'window identity/duplicates/order')
   a=counters(w.get('before'));b=counters(w.get('after'));_require(all(y>=x for x,y in zip(a,b)),'cumulative regression');_require(type(w.get('enabled'))is int and w['enabled']>0 and _same(w.get('running'),w['enabled']),'noMUX');delta.append([y-x for x,y in zip(a,b)])
  empty=[delta[j] for j in (0,1,2,15,16,17)];means=[statistics.mean(v[j] for v in empty) for j in range(6)]
  for ordinal,w in enumerate(ww):
   role=w['role'];rates=[(v-means[j])/h for j,v in enumerate(delta[ordinal])] if role>=0 else None
   if rates is not None:
    target=6 if p['mode']=='d' else 1+2/n;_require(abs(rates[1]-target)<=.005,'actual retired IR/circuit')
   rows.append(dict(mode=p['mode'],epoch=p['epoch'],nodes=n,ordinal=ordinal,role=role,round=w['round'],hops=h,delta=delta[ordinal],rates=rates))
 payload=[r for r in rows if r['role']>=0];qualified=all(r['rates'][2]<=.01 and r['rates'][3]<=.001 for r in payload)
 curves=[]
 for role in range(4):
  points=[];residual=[]
  for n in nodes:
   here=[r for r in payload if r['role']==role and r['nodes']==n];refills=[r['rates'][2] for r in here];v=statistics.median(refills) if all(v<=.01 for v in refills) or all(v>=.1 for v in refills) else .05;points.append((n,v));residual.append(dict(nodes=n,refill_range=[min(refills),max(refills)],walk_max=max(r['rates'][3] for r in here),cache_max=max(r['rates'][4] for r in here),aux_max=max(r['rates'][5] for r in here)))
  curves.append(dict(role=role,stride=p['strides'][role//2],offset='rotating' if role&1 else 'fixed',onset=onset(points),residual=residual,walk_gate=all(x['walk_max']<=.001 for x in residual),cache_gate=all(x['cache_max']<=.01 for x in residual),aux_gate=all(x['aux_max']<=.01 for x in residual)))
 return dict(status='L1_QUALIFIED' if p['phase']=='qualification' and qualified else ('L1_NOT_QUALIFIED' if p['phase']=='qualification' else 'L1_SCAN_COMPLETE'),rows=rows,curves=curves,physical_capacity_certified=False)
