"""Owned leaf PTE capability contract; COW observation cannot backfill steady CONT/HPA.

Protocol docs/design/2026-10-12-translation-self-leaf.md. Pagemap identity must
agree with the actual old/requested descriptors. Untriggered hooks are NOT_EXCITED.
"""
from tools.diagnostic.translation_self_analysis import need,exact,BTF_SHA
MODE='translation-self-leaf'
PROTOCOL='docs/design/2026-10-12-translation-self-leaf.md'
BUILD='docs/reviews/evidence/2026-10-12-translation-self-leaf/build.json'
PLAN='docs/reviews/evidence/2026-10-12-translation-self-leaf/plan.json'
CONSUMER='tools/diagnostic/translation_leaf_analysis.py'
DRIVER='tools/diagnostic/run_sm8650_translation_leaf.py'
def audit_process(records,plan):
 need(type(records)is list and len(records)==1,'leaf record coverage');d=records[0];need(type(d)is dict,'leaf record type')
 if d.get('type')=='failure':
  need(type(d.get('metrics'))is dict and not d['metrics'],'failure empty metrics');f=d.get('failure');need(type(f)is dict and type(f.get('reason'))is str and type(f.get('errno'))is int and f['errno']>=0,'failure descriptor')
  return dict(status='CAPABILITY_UNAVAILABLE' if f['reason']in('bpf-map-create','bpf-program-load','perf-kprobe-open','perf-bpf-attach','kprobe-type') else 'TECHNICAL_FAILURE',failure=f,steady_leaf_cont_state='UNKNOWN',hpa_state='UNKNOWN')
 need(d.get('type')=='leaf-read' and type(plan)is dict and exact(d.get('program'),plan),'actual leaf plan mismatch')
 need(plan.get('probe')==MODE and plan.get('version')==1 and type(plan['version'])is int and plan.get('kernel_hook')=='ptep_set_access_flags','leaf hook identity')
 need(type(plan.get('owner_pid'))is int and 0<plan['owner_pid']<1<<31 and type(plan.get('selected_va'))is int and 0<plan['selected_va']<1<<39 and plan['selected_va']%4096==0,'owner identity')
 need(type(d.get('cpu'))is int and d['cpu']==7 and type(d.get('page_bytes'))is int and d['page_bytes']==4096 and type(d.get('kprobe_type'))is int and d['kprobe_type']>0 and d.get('fds_closed')is True,'runtime cleanup')
 for key,n in [('initial',8),('negative',8),('positive',8),('pagemap_before',2),('pagemap_after',2)]:
  v=d.get(key);need(type(v)is list and len(v)==n and all(type(x)is int and 0<=x<1<<64 for x in v),'leaf snapshot '+key)
 need(d['initial']==d['negative']==[0]*8,'foreign PID/wrong VA capture')
 for wires in (d['pagemap_before'],d['pagemap_after']):need(all(x>>63 and not(x&(1<<62)) and x&((1<<55)-1) for x in wires),'pagemap not visible/present')
 before=[x&((1<<55)-1) for x in d['pagemap_before']];after=[x&((1<<55)-1) for x in d['pagemap_after']];need(before==after and len(set(before))==2,'PFN migration/duplicate')
 if d['positive']==[0]*8:return dict(status='NOT_EXCITED',negative_captures=0,positive_captures=0,steady_leaf_cont_state='UNKNOWN',hpa_state='UNKNOWN')
 stage,va,ptep,old,new,error,hits,pid=d['positive'];need(stage==6 and error==0 and hits==1 and pid==plan['owner_pid'] and va==plan['selected_va'] and ptep>0 and ptep%8==0,'leaf read/count identity')
 need(old&3==new&3==3 and all(((x&((1<<48)-4096))>>12)==before[0] for x in (old,new)),'PTE page/PFN identity')
 return dict(status='SELF_LEAF_DESCRIPTOR_READ',negative_captures=0,positive_captures=1,old_and_requested_pfn_match=True,observed_cont_bit=bool(old&(1<<52)),observed_cont_scope='COW-trigger-entry-only',steady_leaf_cont_state='UNKNOWN',hpa_state='UNKNOWN',physical_entries_certified=False,fds_closed=True)
