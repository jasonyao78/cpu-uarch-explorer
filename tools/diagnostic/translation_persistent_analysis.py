"""Persistent exact-owned registration chain; Linux descriptor identity, not HPA or capacity.

Contract docs/design/2026-10-13-translation-persistent-read.md. Actual dynamic
program is independently regenerated before use; a bad prior state cannot reset.
"""
from tools.diagnostic.translation_self_analysis import need,exact,BTF_SHA
from tools.diagnostic import translation_install_analysis as install
MODE='translation-persistent-read';PROTOCOL='docs/design/2026-10-13-translation-persistent-read.md';BUILD='docs/reviews/evidence/2026-10-13-translation-persistent-read/build.json';PLAN='docs/reviews/evidence/2026-10-13-translation-persistent-read/plan.json';CONSUMER='tools/diagnostic/translation_persistent_analysis.py';DRIVER='tools/diagnostic/run_sm8650_translation_persistent.py';PA_MASK=(1<<48)-4096;PFN_MASK=(1<<55)-1

def vector(v,n,label):need(type(v)is list and len(v)==n and all(type(x)is int and 0<=x<1<<64 for x in v),'persistent vector '+label);return v
def pfns(v,n,label):
 vector(v,n,label);need(all(x>>63 and not(x&(1<<62)) and x&PFN_MASK for x in v),'persistent present PFN '+label);return [x&PFN_MASK for x in v]
def payload(p,pid,va,pfn):
 need(p[:5]==[13,1,1,pid,va] and not any(p[13:16]),'persistent paired or sticky failure');need(all(p[i]>0 and p[i]%8==0 for i in (5,6,7,9,10)),'persistent pointers');need(p[6]%4096==8*((va>>21)&511) and p[7]%4096==8*((va>>12)&511),'persistent table indices');need(all(p[i]&3==3 and p[i]&PA_MASK for i in (8,11,12)) and (p[12]&PA_MASK)//4096==pfn,'persistent descriptor/PFN');b0=((p[6]&~4095)-(p[11]&PA_MASK))% (1<<64);b1=((p[7]&~4095)-(p[8]&PA_MASK))%(1<<64);need(b0!=0 and b0==b1,'persistent two independent level relations');return b0

def audit_process(rr,plan):
 need(type(rr)is list and rr and all(type(r)is dict for r in rr),'persistent records')
 if len(rr)==1 and rr[0].get('type')=='failure':return install.audit_process(rr,None)
 need(type(plan)is dict and exact(rr[0],plan),'persistent actual plan mismatch');pid=plan.get('owner_pid');fd=plan.get('map_fd');need(type(pid)is int and 0<pid<1<<31 and type(fd)is int and 0<=fd<1<<31,'persistent owner/map');need(plan.get('probe')==MODE and plan.get('kernel_hook')=='do_set_pte' and all(type(plan.get(k))is int and plan[k]==v for k,v in [('version',1),('value_bytes',136),('request_word',16),('vmf_pmd',48),('vmf_pte',88),('task_mm',1440),('mm_pgd',56)]),'persistent BTF/registration contract');need(len(rr)>=3,'persistent mapping missing');mapping=rr[1];need(mapping.get('type')=='mapping' and all(type(mapping.get(k))is int and mapping[k]==v for k,v in [('cpu',7),('page_bytes',4096),('nodes',8)]),'persistent mapping');base=mapping.get('alias_base');canonical=mapping.get('canonical_base');scratch=mapping.get('scratch_base');need(all(type(v)is int and 0<v<1<<39 and v%4096==0 for v in (base,canonical,scratch)) and len({base,canonical,scratch})==3 and type(mapping.get('kprobe_type'))is int and mapping['kprobe_type']>0,'persistent owned bases');need(rr[2].get('type')=='canonical-before','persistent canonical before');pf=pfns(rr[2].get('entries'),8,'canonical before');need(len(set(pf))==8,'persistent canonical uniqueness');previous=[0]*17;mm=set();pgd=set();bias=set();cont=[]
 for node in range(8):
  cursor=3+node;need(cursor<len(rr),'persistent missing capture');r=rr[cursor]
  if r.get('type')=='failure':need(cursor==len(rr)-1,'persistent first failure terminal');v=install.audit_process([r],None);return dict(v,captures=node)
  va=base+8192*node;need(r.get('type')=='persistent-read' and type(r.get('node'))is int and r['node']==node and type(r.get('selected_va'))is int and r['selected_va']==va and type(r.get('node_word'))is int and r['node_word']==0x12340000+node and type(r.get('cpu'))is int and r['cpu']==7 and r.get('observer_active')is True,'persistent node/word/runtime')
  for key in ('previous','initial','negative','positive'):vector(r.get(key),17,key)
  request=[0]*16+[va];need(r['previous']==previous and r['initial']==r['negative']==request,'persistent registration/reset/negative chain')
  if node==0:need(vector(r.get('foreign'),17,'foreign')==request,'persistent foreign PID capture')
  else:need(r.get('foreign') is None,'persistent foreign negative measured once only')
  pair=[pf[node],pf[node^1]]
  for key in ('canonical_before','canonical_after','alias_after'):need(pfns(r.get(key),2,key)==pair,'persistent canonical identity/migration')
  before=vector(r.get('alias_before'),2,'alias before');need(all(not(x>>63) and not(x&(1<<62)) and not(x&PFN_MASK) for x in before),'persistent initially absent aliases');p=r['positive'];need(p[16]==va,'persistent request survived')
  if p==request:
   need(cursor+1==len(rr)-1 and exact(rr[-1],dict(type='stop',reason='not-excited',captures=node+1)),'persistent first no-capture terminal');return dict(status='NOT_EXCITED',captures=node+1,steady_cont_state='UNKNOWN',hpa_state='UNKNOWN',physical_entries_certified=False)
  relation=payload(p,pid,va,pf[node]);mm.add(p[9]);pgd.add(p[10]);bias.add(relation);cont.append(bool(p[12]&(1<<52)));previous=p
 need(len(rr)==12 and rr[-1].get('type')=='final' and rr[-1].get('fds_closed')is True and pfns(rr[-1].get('canonical_after'),8,'canonical after')==pf,'persistent final/FD/PFN');need(len(mm)==len(pgd)==len(bias)==1,'persistent same mm/pgd/relation')
 return dict(status='OWNED_PERSISTENT_DESCRIPTOR_READ',captures=8,foreign_negative_captures=0,wrong_va_negative_captures=0,program_loads=2,observer_map_count=1,foreign_child_calls=1,all_registration_chains_exact=True,canonical_alias_pfn_match=True,two_level_relation_equal=True,observed_installation_cont=cont,steady_cont_state='UNKNOWN',hpa_state='UNKNOWN',physical_entries_certified=False,fds_closed=True)
