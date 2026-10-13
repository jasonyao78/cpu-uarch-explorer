"""Actual descriptor-bound shared graph -> mandatory hardware gates -> finite reach.

Contract docs/design/2026-10-13-tlb-observed-reach.md. Descriptor addresses are
Linux PA/IPA; per-process point/interval outputs do not certify physical capacity.
"""
import statistics as st
from tools.diagnostic import translation_persistent_analysis as owned
from tools.diagnostic.translation_self_analysis import need,exact,BTF_SHA
MODE='tlb-observed-reach';PROTOCOL='docs/design/2026-10-13-tlb-observed-reach.md';BUILD='docs/reviews/evidence/2026-10-13-tlb-observed-reach/build.json';PLAN='docs/reviews/evidence/2026-10-13-tlb-observed-reach/plan.json';CONSUMER='tools/diagnostic/tlb_observed_reach_analysis.py';DRIVER='tools/diagnostic/run_sm8650_tlb_observed_reach.py';RAW='tools/diagnostic/tlb_observed_reach_raw.py';GRID=(32,1024,1536,1792,2048,2304);EVENTS=(17,8,5,52,3,1)
def conditions(phase):
 need(phase in ('qualification','scan'),'observed reach phase');return [dict(name=f'e{e}-n{n}-r{e%2}',args=['--run','--nodes',str(n),'--reverse',str(e%2)]) for e in range(3) for n in ((32,) if phase=='qualification' else (GRID[::-1] if e%2 else GRID))]
def expected(n,r):
 order=list(range(n));seed=137
 for i in range(n-1,0,-1):seed=(1664525*seed+1013904223)%(1<<32);j=seed%(i+1);order[i],order[j]=order[j],order[i]
 if r:order.reverse()
 nxt=[0]*n
 for i,j in enumerate(order):nxt[j]=order[(i+1)%n]
 return dict(probe=MODE,version=1,nodes=n,reverse=bool(r),captures=2*n,windows=12,rounds=3,order_seed=137,load_budget=1048576,loads=n*((1048576+n-1)//n),strides=[12288,2109440],base_alignment=1<<33,base_gap=1<<30,reserve_bytes=1<<34,observer_cool_seconds=15,events=list(EVENTS),pmu_type=8,kernel_words=[0xf9400000,0x9b092800,0xf1000508,0x54ffffa1],order=order,next=nxt)
def plans():return {f'{n}:{r}':expected(n,r) for n in GRID for r in (0,1)}
def failure(d,captures):
 v=owned.install.audit_process([d],None)
 if d['failure']['reason']=='perf-open':v['status']='CAPABILITY_UNAVAILABLE'
 return dict(v,captures=captures)
def fields(d,w,label):need(type(d)is dict and all(k in d and exact(d[k],v) for k,v in w.items()),'observed '+label)
def audit_process(rr,program,c,registered):
 need(exact(registered,plans()),'observed actual registered layouts');return _audit_records(rr,program,c)
def _audit_records(rr,program,c):
 need(type(rr)is list and rr and all(type(r)is dict for r in rr),'observed record objects');n=int(c['args'][2]);rev=int(c['args'][4]);need(n in GRID and rev in (0,1),'observed requested grid')
 if len(rr)==1 and rr[0].get('type')=='failure':return failure(rr[0],0)
 need(len(rr)>=4 and exact(rr[0],expected(n,rev)) and exact(rr[1],program),'observed configuration or actual observer plan');pid=program.get('owner_pid');fd=program.get('map_fd');need(type(pid)is int and 0<pid<1<<31 and type(fd)is int and 0<=fd<1<<31,'observed owner/map')
 fields(program,dict(probe='translation-persistent-read',version=1,value_bytes=136,request_word=16,kernel_hook='do_set_pte',vmf_pmd=48,vmf_pte=88,task_mm=1440,mm_pgd=56),'observer BTF');mapping=rr[2];fields(mapping,dict(type='mapping',cpu=7,page_bytes=4096,nodes=n),'mapping');base=mapping.get('bases');canonical=mapping.get('canonical_base');scratch=mapping.get('scratch_base');need(type(base)is list and len(base)==2 and all(type(v)is int and 0<v<1<<39 and v%4096==0 for v in base) and base[0]%(1<<33)==0 and base[1]-base[0]==1<<30 and all(type(v)is int and 0<v<1<<39 and v%4096==0 for v in (canonical,scratch)) and type(mapping.get('kprobe_type'))is int and mapping['kprobe_type']>0,'observed owned bases');regions=[(base[0],base[0]+rr[0]['strides'][0]*(n-1)+4096),(base[1],base[1]+rr[0]['strides'][1]*(n-1)+4096),(canonical,canonical+n*4096),(scratch,scratch+12288)];need(all(max(a,c0)>=min(b,d) for i,(a,b) in enumerate(regions) for c0,d in regions[i+1:]),'observed nonoverlap');fields(rr[3],dict(type='canonical-before'),'canonical before');pf=owned.pfns(rr[3].get('entries'),n,'canonical-before');need(len(set(pf))==n,'observed canonical unique');previous=[0]*17;mm=set();pgd=set();bias=set();roots=set();shapes=[dict(pt=set(),pmd=set(),leafline=set(),pmdline=set(),cont=[]) for _ in range(2)];cursor=4
 for position in range(2):
  shape=1-position if rev else position;stride=rr[0]['strides'][shape];out=shapes[shape]
  for node in range(n):
   need(cursor<len(rr),'observed missing capture');r=rr[cursor];capture=position*n+node
   if r.get('type')=='failure':need(cursor==len(rr)-1,'observed first failure terminal');return failure(r,capture)
   va=base[shape]+stride*node;fields(r,dict(type='observed-read',capture=capture,shape=shape,node=node,selected_va=va,node_word=rr[0]['next'][node],cpu=7,observer_active=True),'capture identity')
   for key in ('previous','initial','negative','positive'):owned.vector(r.get(key),17,key)
   request=[0]*16+[va];need(r['previous']==previous and r['initial']==r['negative']==request,'observed registration/reset/negative chain');need(owned.vector(r.get('foreign'),17,'foreign')==request if capture==0 else r.get('foreign') is None,'observed foreign negative once');pair=[pf[node],pf[node^1]]
   for key in ('canonical_before','canonical_after','alias_after'):need(owned.pfns(r.get(key),2,key)==pair,'observed canonical/alias identity')
   before=owned.vector(r.get('alias_before'),2,'alias-before');need(all(not(x>>63) and not(x&(1<<62)) and not(x&owned.PFN_MASK) for x in before),'observed initially absent');p=r['positive'];need(p[16]==va,'observed request survived');cursor+=1
   if p==request:need(cursor==len(rr)-1 and exact(rr[-1],dict(type='stop',reason='not-excited',captures=capture+1)),'observed first empty terminal');return dict(status='NOT_EXCITED',captures=capture+1,physical_capacity_certified=False)
   relation=owned.payload(p,pid,va,pf[node]);mm.add(p[9]);pgd.add(p[10]);bias.add(relation);roots.add((p[10]+8*((va>>30)&511))//64);pt=p[8]&owned.PA_MASK;pmd=p[11]&owned.PA_MASK;out['pt'].add(pt);out['pmd'].add(pmd);out['leafline'].add((pt+8*((va>>12)&511))//64);out['pmdline'].add((pmd+8*((va>>21)&511))//64);out['cont'].append(bool(p[12]&(1<<52)));previous=p
 def next_record():
  nonlocal cursor
  need(cursor<len(rr),'observed missing terminal/window');v=rr[cursor];cursor+=1;return v
 close=next_record()
 if close.get('type')=='failure':need(cursor==len(rr),'observed failure terminal');return failure(close,2*n)
 fields(close,dict(type='observer-final',fds_closed=True),'observer unload');runtime=next_record()
 if runtime.get('type')=='failure':need(cursor==len(rr),'observed perf failure terminal');return failure(runtime,2*n)
 fields(runtime,dict(type='perf-runtime',cpu=7,observer_closed=True),'perf runtime');ids=runtime.get('event_ids');need(type(ids)is list and len(ids)==6 and all(type(v)is int and 0<v<1<<64 for v in ids) and len(set(ids))==6,'observed six IDs');schedule=[('empty-before',r,-1) for r in range(3)]+[('data',r,(r+p+rev)%2) for r in range(3) for p in range(2)]+[('empty-after',r,-1) for r in range(3)];samples=[]
 for phase,r,shape in schedule:
  z=next_record()
  if z.get('type')=='failure':need(cursor==len(rr),'observed window failure terminal');return failure(z,2*n)
  loads=rr[0]['loads'] if phase=='data' else 0;fields(z,dict(type='round',phase=phase,round=r,shape=shape,loads=loads,cpu=7,head_returned=True,observer_closed=True),'window schedule');need(all(type(z.get(k))is int and 0<z[k]<1<<64 for k in ('enabled','running')) and z['enabled']==z['running'],'observed window time/MUX');counts=z.get('counts');need(type(counts)is list and len(counts)==6 and all(type(v)is int and 0<=v<1<<64 for v in counts) and counts[0]>0,'observed typed counts');samples.append(z)
 for shape in (0,1):
  last=next_record();fields(last,dict(type='graph-final',shape=shape),'graph final');need(owned.pfns(last.get('entries'),n,'graph-final')==pf and exact(last.get('words'),rr[0]['next']),'observed final graph words/PFN')
 final=next_record();fields(final,dict(type='final',fds_closed=True),'final FD');need(owned.pfns(final.get('canonical_after'),n,'canonical-after')==pf and cursor==len(rr),'observed final coverage/PFN');need(len(mm)==len(pgd)==len(bias)==len(roots)==1,'observed same mm/pgd/two-level relation/root virtual line')
 return dict(condition=c['name'],args=c['args'],status='complete',config=rr[0],program=program,raw_records=rr,samples=samples,descriptor_shapes=[dict(shape=i,leaf_table_pages=len(v['pt']),pmd_table_pages=len(v['pmd']),linux_leaf_64B_groups=len(v['leafline']),linux_pmd_64B_groups=len(v['pmdline']),observed_installation_cont=v['cont']) for i,v in enumerate(shapes)])
def onset(points):
 states=[1 if all(v>=.10 for v in p['walk_rates']) else 0 if all(v<.10 for v in p['walk_rates']) else -1 for p in points]
 above=[i for i,v in enumerate(states) if v==1]
 if above and any(v==0 for v in states[above[0]:]):return dict(status='non-monotone')
 if -1 in states:return dict(status='ambiguous')
 if not above:return dict(status='no-onset-through-grid')
 first=above[0]
 if first==0:return dict(status='left-censored')
 if len(points)-first<2:return dict(status='right-censored')
 return dict(status='operational-interval',interval=[points[first-1]['nodes'],points[first]['nodes']])
def analyze(run):
 need(run.get('mode')==MODE,'observed matrix mode');phase=run.get('phase');cc=conditions(phase);rows=run.get('rows');need(type(rows)is list and len(rows)==len(cc),'observed process coverage');processed=[];pids=[]
 for row,c in zip(rows,cc):
  fields(row,dict(condition=c['name'],args=c['args'],status='complete'),'row identity');checked=_audit_records(row['raw_records'],row['program'],c);need(exact(checked['samples'],row['samples']) and exact(checked['descriptor_shapes'],row['descriptor_shapes']),'observed summary binding');pids.append(row['program']['owner_pid']);n=row['config']['nodes'];loads=row['config']['loads'];empty=[s for s in row['samples'] if s['phase']!='data'];background=[st.mean(s['counts'][i] for s in empty) for i in range(6)];data=[s for s in row['samples'] if s['phase']=='data'];g=dict(retired_IR=all(abs(s['counts'][1]/loads-4)<=.001 for s in data),instruction_background=all(s['counts'][5]/loads<=.001 for s in data));curves=[dict(shape=i,nodes=n,walk_rates=[(s['counts'][3]-background[3])/loads for s in data if s['shape']==i],counts_by_event={hex(e):[(s['counts'][j]-background[j])/loads for s in data if s['shape']==i] for j,e in enumerate(EVENTS)}) for i in (0,1)];d=[curves[1]['walk_rates'][i]-curves[0]['walk_rates'][i] for i in range(3)];processed.append(dict(process=c['name'],nodes=n,reverse=row['config']['reverse'],gates=g,background_mean=background,curves=curves,spaced_minus_packed=d,descriptor_shapes=row['descriptor_shapes'],qualified=all(g.values())))
 need(len(set(pids))==len(pids),'observed fresh owners');good=all(v['qualified'] for v in processed);n0=[v for v in processed if v['nodes']==32];floor=all(all(abs(r)<=.01 for c in v['curves'] for r in c['walk_rates']) for v in n0);good=good and floor;out=dict(mode=MODE,phase=phase,windows=len(rows)*12,processes=processed,floor_negative=floor,physical_capacity_certified=False,physical_ways_certified=False,hpa_state='UNKNOWN',steady_cont_state='UNKNOWN')
 if phase=='qualification':out['status']='OBSERVED_GRAPH_QUALIFIED' if good else 'OBSERVED_GRAPH_NOT_QUALIFIED';return out
 comparisons=[];curves=[]
 for n in GRID:
  cells=[v for v in processed if v['nodes']==n];d=[r for v in cells for r in v['spaced_minus_packed']];comparisons.append(dict(nodes=n,differences=d,status='replicated_geometry_difference' if good and all(v>=.10 for v in d) else 'not-replicated' if good else 'INCOMPUTABLE'))
 for e in range(3):
  for shape in (0,1):
   points=sorted([v['curves'][shape] for v in processed if v['process'].startswith(f'e{e}-')],key=lambda p:p['nodes']);curves.append(dict(epoch=e,shape=shape,points=points,onset=onset(points) if good else dict(status='INCOMPUTABLE')))
 out.update(status='DESCRIPTOR_BOUND_GEOMETRY_DIFFERENCE' if good and any(v['status']=='replicated_geometry_difference' for v in comparisons) else 'INCONCLUSIVE',comparisons=comparisons,curves=curves);return out
