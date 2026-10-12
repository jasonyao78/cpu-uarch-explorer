"""Own shared installation hierarchy; no guessed bias, retrospective CONT or capacity.

Contract docs/design/2026-10-12-translation-installation-read.md. Only typed,
paired entry/return descriptors with two independent level relations may qualify.
"""
from tools.diagnostic.translation_self_analysis import need,exact,BTF_SHA
MODE='translation-installation-read'
PROTOCOL='docs/design/2026-10-12-translation-installation-read.md'
BUILD='docs/reviews/evidence/2026-10-12-translation-installation-read/build.json'
PLAN='docs/reviews/evidence/2026-10-12-translation-installation-read/plan.json'
CONSUMER='tools/diagnostic/translation_install_analysis.py'
DRIVER='tools/diagnostic/run_sm8650_translation_install.py'
MASK64=(1<<64)-1;PA_MASK=(1<<48)-4096;PFN_MASK=(1<<55)-1
def audit_process(records,plan):
 need(type(records)is list and len(records)==1,'installation record coverage');d=records[0];need(type(d)is dict,'installation record type')
 if d.get('type')=='failure':
  need(type(d.get('metrics'))is dict and not d['metrics'],'failure empty metrics');f=d.get('failure');need(type(f)is dict and type(f.get('reason'))is str and type(f.get('errno'))is int and f['errno']>=0,'failure descriptor')
  return dict(status='CAPABILITY_UNAVAILABLE' if f['reason']in('bpf-map-create','bpf-program-load','perf-kprobe-open','perf-bpf-attach','kprobe-type') else 'TECHNICAL_FAILURE',failure=f,steady_cont_state='UNKNOWN',hpa_state='UNKNOWN')
 need(d.get('type')=='install-read' and type(plan)is dict and exact(d.get('program'),plan),'actual installation plan mismatch')
 need(plan.get('probe')==MODE and plan.get('kernel_hook')=='do_set_pte' and all(type(plan.get(k))is int and plan[k]==v for k,v in [('version',1),('vmf_pmd',48),('vmf_pte',88),('task_mm',1440),('mm_pgd',56)]),'hook/BTF contract')
 pid=plan.get('owner_pid');va=plan.get('selected_va');need(type(pid)is int and 0<pid<1<<31 and type(va)is int and 0<va<1<<39 and va%4096==0,'owned identity')
 need(type(d.get('cpu'))is int and d['cpu']==7 and type(d.get('page_bytes'))is int and d['page_bytes']==4096 and type(d.get('kprobe_type'))is int and d['kprobe_type']>0 and d.get('fds_closed')is True,'runtime/cleanup')
 for key,n in [('initial',16),('negative',16),('positive',16),('alias_before',2),('alias_after',2),('canonical_before',2),('canonical_after',2)]:
  v=d.get(key);need(type(v)is list and len(v)==n and all(type(x)is int and 0<=x<1<<64 for x in v),'installation snapshot '+key)
 need(d['initial']==d['negative']==[0]*16,'foreign PID/wrong VA capture')
 need(all(not(x&(1<<63)) and not(x&(1<<62)) and not(x&PFN_MASK) for x in d['alias_before']),'aliases must be initially absent')
 for key in ('canonical_before','canonical_after','alias_after'):need(all(x>>63 and not(x&(1<<62)) and x&PFN_MASK for x in d[key]),'pagemap presence '+key)
 pfns=[x&PFN_MASK for x in d['canonical_before']];need(len(set(pfns))==2 and all([x&PFN_MASK for x in d[k]]==pfns for k in ('canonical_after','alias_after')),'canonical/alias identity or migration')
 out=d['positive']
 if out==[0]*16:return dict(status='NOT_EXCITED',entry_captures=0,return_captures=0,canonical_alias_pfn_match=True,steady_cont_state='UNKNOWN',hpa_state='UNKNOWN')
 stage,entries,returns,owner,address,vmf,pmdp,ptep,pmdval,mm,pgd,pgdval,pteval,error,zero0,zero1=out
 need(stage==13 and entries==returns==1 and owner==pid and address==va and error==0 and zero0==zero1==0,'entry/return pairing or sticky failure')
 need(all(x>0 and x%8==0 for x in (vmf,pmdp,ptep,mm,pgd)),'kernel pointers')
 need(pmdp%4096==8*((va>>21)&511) and ptep%4096==8*((va>>12)&511),'owned table entry indices')
 need(all(word&3==3 and word&PA_MASK for word in (pmdval,pgdval,pteval)),'descriptor types')
 need((pteval&PA_MASK)>>12==pfns[0],'installed leaf PFN mismatch')
 bpmd=((pmdp&~4095)-(pgdval&PA_MASK))&MASK64;bpte=((ptep&~4095)-(pmdval&PA_MASK))&MASK64
 need(bpmd==bpte and bpmd!=0,'two independent level relations differ')
 return dict(status='OWNED_SHARED_DESCRIPTOR_HIERARCHY_READ',entry_captures=1,return_captures=1,leaf_pfn_matches_canonical=True,canonical_alias_pfn_match=True,two_level_relation_equal=True,linux_parent_descriptor_pages_observed=2,observed_cont_bit=bool(pteval&(1<<52)),observed_cont_scope='initial-shared-read-installation-only',steady_cont_state='UNKNOWN',hpa_state='UNKNOWN',physical_entries_certified=False,machine_dram_pa_certified=False,fds_closed=True)
