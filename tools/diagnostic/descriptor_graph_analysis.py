"""Bind actual shared ordinal graph and Linux descriptor identities, before capacity inference.

Frozen docs/design/2026-10-13-tlb-descriptor-graph.md. First failure/empty hook
stops; whole physical graph and parent layout must qualify, never guessed from VA.
"""
from tools.diagnostic import translation_install_analysis as install
from tools.diagnostic.translation_self_analysis import need,exact,BTF_SHA
MODE='tlb-descriptor-graph';PROTOCOL='docs/design/2026-10-13-tlb-descriptor-graph.md'
BUILD='docs/reviews/evidence/2026-10-13-tlb-descriptor-graph/build.json';PLAN='docs/reviews/evidence/2026-10-13-tlb-descriptor-graph/plan.json'
CONSUMER='tools/diagnostic/descriptor_graph_analysis.py';DRIVER='tools/diagnostic/run_sm8650_descriptor_graph.py'
PA_MASK=(1<<48)-4096;PFN_MASK=(1<<55)-1

def expected_plan():
 order=list(range(32));seed=137
 for i in range(31,0,-1):seed=(1664525*seed+1013904223)%(1<<32);j=seed%(i+1);order[i],order[j]=order[j],order[i]
 nxt=[0]*32
 for i,j in enumerate(order):nxt[j]=order[(i+1)%32]
 return dict(probe=MODE,version=1,nodes=32,captures=64,seed=137,loads=512,packed_stride=8192,spaced_stride=2105344,base_alignment=1<<31,base_gap=1<<30,observer='do_set_pte-entry-return-99-32',kernel_words=[0xf9400000,0x9b092800,0xf1000508,0x54ffffa1],order=order,next=nxt)
def pfn_vector(v,n,label):
 need(type(v)is list and len(v)==n and all(type(x)is int and 0<=x<1<<64 and x>>63 and not(x&(1<<62)) and x&PFN_MASK for x in v),'graph pagemap '+label);return [x&PFN_MASK for x in v]
def audit_process(records,plans,registered):
 need(exact(registered,expected_plan()),'graph registered plan drift');need(type(records)is list and records and all(type(x)is dict for x in records),'graph record objects');need(type(plans)is list,'graph dynamic plan list')
 if len(records)==1 and records[0].get('type')=='failure':return install.audit_process(records,None)
 need(len(records)>=3 and exact(records[0],registered),'graph configuration');mapping=records[1];need(mapping.get('type')=='mapping' and type(mapping.get('nodes'))is int and mapping['nodes']==32,'graph mapping');pid=mapping.get('owner_pid');bases=mapping.get('bases');canonical=mapping.get('canonical_base');need(type(pid)is int and 0<pid<1<<31 and type(bases)is list and len(bases)==2 and all(type(v)is int and 0<v<1<<39 for v in bases) and bases[0]%(1<<31)==0 and bases[1]-bases[0]==1<<30 and type(canonical)is int and 0<canonical<1<<39 and canonical%4096==0,'graph owned bases')
 need(records[2].get('type')=='canonical-before','graph canonical before');pfns=pfn_vector(records[2].get('entries'),32,'canonical-before');need(len(set(pfns))==32,'graph canonical uniqueness')
 cursor=3;captured=0;shapes=[];all_mm=set();all_pgd=set();all_bias=set();root_lines=set();stopped=False
 for shape,stride in enumerate((8192,2105344)):
  ptpages=set();pmdpages=set();leaflines=set();pmdlines=set();cont=[]
  for node in range(32):
   need(cursor<len(records),'graph missing capture');row=records[cursor]
   if row.get('type')=='failure':
    need(cursor==len(records)-1 and captured==len(plans),'graph failure must terminate');v=install.audit_process([row],None);return dict(v,captures=captured,physical_capacity_certified=False)
   need(row.get('type')=='install-read' and type(row.get('shape'))is int and row['shape']==shape and type(row.get('node'))is int and row['node']==node and type(row.get('node_word'))is int and row['node_word']==registered['next'][node],'graph capture identity/ordinal');need(captured<len(plans),'graph missing dynamic plan');plan=plans[captured];need(type(plan)is dict and type(plan.get('owner_pid'))is int and plan['owner_pid']==pid and type(plan.get('selected_va'))is int and plan['selected_va']==bases[shape]+stride*node,'graph selected address/owner')
   v=install.audit_process([row],plan);pair=[pfns[node],pfns[node^1]]
   for field in ('canonical_before','canonical_after','alias_after'):need(pfn_vector(row[field],2,field)==pair,'graph canonical/node PFN binding')
   captured+=1;cursor+=1
   if v['status']=='NOT_EXCITED':
    need(cursor==len(records)-1 and exact(records[cursor],dict(type='stop',reason='not-excited',captures=captured)) and captured==len(plans),'graph first empty hook must stop');return dict(status='NOT_EXCITED',captures=captured,physical_capacity_certified=False,steady_cont_state='UNKNOWN',hpa_state='UNKNOWN')
   need(v['status']=='OWNED_SHARED_DESCRIPTOR_HIERARCHY_READ','graph capture must qualify');out=row['positive'];va=plan['selected_va'];pt=out[8]&PA_MASK;pmd=out[11]&PA_MASK;ptpages.add(pt);pmdpages.add(pmd);leaflines.add((pt+8*((va>>12)&511))//64);pmdlines.add((pmd+8*((va>>21)&511))//64);all_mm.add(out[9]);all_pgd.add(out[10]);all_bias.add(((out[6]&~4095)-pmd)%(1<<64));root_lines.add((out[10]+8*((va>>30)&511))//64);cont.append(bool(out[12]&(1<<52)))
  need(cursor<len(records),'graph missing final');last=records[cursor];need(last.get('type')=='graph-final' and type(last.get('shape'))is int and last['shape']==shape and type(last.get('loads'))is int and last['loads']==512 and last.get('head_returned')is True and exact(last.get('words'),registered['next']) and pfn_vector(last.get('entries'),32,'alias-final')==pfns,'graph closed chain/final PFN');cursor+=1
  shapes.append(dict(shape=shape,leaf_table_pages=len(ptpages),pmd_table_pages=len(pmdpages),leaf_entry_lines=len(leaflines),pmd_entry_lines=len(pmdlines),observed_installation_cont=cont,graph_head_returned=True,stored_ordinals_identical=True,canonical_alias_pfn_match=True))
 need(cursor==len(records)-1 and captured==len(plans)==64,'graph terminal coverage');last=records[cursor];need(last.get('type')=='canonical-after' and pfn_vector(last.get('entries'),32,'canonical-after')==pfns,'graph canonical final/migration');need(len(all_mm)==len(all_pgd)==len(all_bias)==len(root_lines)==1,'graph same mm/pgd/two-level relation/root virtual line');need([x['leaf_table_pages'] for x in shapes]==[1,32] and [x['leaf_entry_lines'] for x in shapes]==[8,32],'graph actual descriptor layout excitation')
 return dict(status='DESCRIPTOR_GRAPH_BOUND',captures=64,shapes=shapes,canonical_data_pages=32,alias_nodes=64,same_mm=True,same_root_virtual_line=True,two_level_relation_equal=True,physical_capacity_certified=False,steady_cont_state='UNKNOWN',hpa_state='UNKNOWN',naming_limit='actual ordinal graph and initial-installation Linux descriptor identity; no PMU/capacity inference')
