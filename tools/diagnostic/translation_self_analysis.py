"""Self-only kernel read qualification; no leaf/PTE CONT or capacity certification.

Contract: docs/design/2026-10-12-translation-self-read.md. Actual producer plans
are mandatory input; output exposes counts and predicates, never addresses/PFNs.
"""
MODE='translation-self-read'
BTF_SHA='edf0efa6c0a4d661367567ae7386985c58e42d6e4cc700a0903f8eb831c6c6e1'
PROTOCOL='docs/design/2026-10-12-translation-self-read.md'
BUILD='docs/reviews/evidence/2026-10-12-translation-self-read/build.json'
PLAN='docs/reviews/evidence/2026-10-12-translation-self-read/plan.json'
CONSUMER='tools/diagnostic/translation_self_analysis.py'
DRIVER='tools/diagnostic/run_sm8650_translation_self.py'

def need(condition,reason):
 if not condition:raise ValueError(reason)

def exact(a,b):
 if type(a) is not type(b):return False
 if type(a) is dict:return a.keys()==b.keys() and all(exact(a[k],b[k]) for k in a)
 if type(a) is list:return len(a)==len(b) and all(exact(x,y) for x,y in zip(a,b))
 return a==b

def audit_process(records,plan):
 """Exactly one producer result; denial retains empty metrics, technical drift rejects."""
 need(type(records)is list and len(records)==1,'self-read record coverage')
 d=records[0];need(type(d)is dict,'record type')
 if d.get('type')=='failure':
  need(d.get('metrics')=={} and type(d.get('metrics'))is dict,'failure metrics must be empty')
  f=d.get('failure');need(type(f)is dict and type(f.get('reason'))is str and type(f.get('errno'))is int and f['errno']>=0,'failure descriptor')
  return dict(status='CAPABILITY_UNAVAILABLE' if f['reason'] in ('bpf-map-create','bpf-program-load','bpf-raw-attach') else 'TECHNICAL_FAILURE',failure=f,leaf_cont_state='UNKNOWN',hpa_state='UNKNOWN')
 need(d.get('type')=='self-read' and type(plan)is dict,'success needs actual plan')
 need(exact(d.get('program'),plan),'actual bytecode/config mismatch')
 need(type(d.get('cpu'))is int and d['cpu']==7 and type(d.get('page_bytes'))is int and d['page_bytes']==4096 and d.get('fds_closed')is True,'runtime/cleanup contract')
 need(all(plan.get(k)==v and type(plan.get(k))is int for k,v in [('version',1),('task_mm',1440),('task_tgid',1588),('mm_pgd',56),('syscall_id',172)]),'BTF layout and syscall contract')
 va=d.get('va');need(type(va)is list and len(va)==2 and all(type(v)is int and 0<v<1<<39 and v%4096==0 for v in va),'owned VA shape')
 need(va[1]-va[0]==1<<30 and plan.get('root_indices')==[(v>>30)&511 for v in va],'owned root index mismatch')
 for key in ('initial','negative','positive'):
  v=d.get(key);need(type(v)is list and len(v)==8 and all(type(x)is int and 0<=x<1<<64 for x in v),'snapshot shape '+key)
 need(d['initial']==[0]*8 and d['negative']==[0]*8,'foreign PID/wrong syscall capture')
 stage,pid,mm,pgd,desc0,desc1,errno,hits=d['positive']
 need(stage==6 and pid==plan['owner_pid'] and type(plan['owner_pid'])is int and mm>0 and pgd>0 and errno==0 and hits==3,'owned read/count qualification')
 need(desc0&3==3 and desc1&3==3,'root descriptors not tables')
 return dict(status='SELF_ROOT_DESCRIPTOR_READ',kernel_reads_per_capture=5,negative_captures=0,positive_captures=3,root_table_descriptors=2,owner_tgid_matches=True,fds_closed=True,leaf_cont_state='UNKNOWN',hpa_state='UNKNOWN',physical_entries_certified=False)
