"""真实C++计划/布局→严格消费者；外部PMU和PFN为软件合成，不能作真机证据。

冻结契约：docs/design/2026-10-12-tlb-pfn-association.md。
"""
import copy,importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class AssociationAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  source=ROOT/'probes/diagnostic/tlb_pfn_association.cpp'
  if not source.exists():raise AssertionError('association producer missing')
  cls.temp=tempfile.TemporaryDirectory();cls.folder=Path(cls.temp.name);cls.exe=cls.folder/'producer'
  subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(source),'-o',str(cls.exe)],check=True)
  cls.actual={k:[json.loads(l) for l in subprocess.check_output([str(cls.exe),'--plan',*opt],text=True).splitlines()] for k,opt in [('forward',[]),('reverse',['--reverse'])]}
  cls.layouts={}
  for gapped in (False,True):
   for rev in (False,True):
    pfns=[12345+i*(3 if gapped else 1) for i in range(4096)]
    result=subprocess.run([str(cls.exe),'--layout','4294967296',*(['--reverse'] if rev else [])],input=' '.join(map(str,pfns))+'\n',text=True,capture_output=True,check=True)
    cls.layouts[gapped,rev]=[json.loads(l) for l in result.stdout.splitlines()]
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def module(self):return importlib.import_module('tools.diagnostic.tlb_association_analysis')
 def records(self,reverse=False,effect='sensitive',gapped=False):
  m=self.module();layout=copy.deepcopy(self.layouts[gapped,reverse]);back=layout[1];cp=[12345+i*(3 if gapped else 1) for i in range(4096)];back.update(canonical_base=85899345920,canonical_pfns=cp,canonical_entries=[(1<<63)|(1<<56)|p for p in cp]);rr=[layout[0],dict(type='pmu',ids=list(range(101,107))),back]
  for c,g in zip(layout[2::2],layout[3::2]):
   rr.extend([c,g])
   for stage in ('before','after'):
    rr.extend([dict(type='backing',cell=c['cell'],stage=stage,kernel_page_kb=4,mmu_page_kb=4,anon_huge_kb=0,shmem_pmd_kb=0,file_pmd_kb=0),dict(type='pfn-certificate',cell=c['cell'],stage=stage,alias_pfns=cp[:c['n']],alias_entries=back['canonical_entries'][:c['n']],canonical_pfns=cp[:c['n']],canonical_entries=back['canonical_entries'][:c['n']]),dict(m.graph(c,g,back['arena_base']),type='graph-certificate',stage=stage)])
   loads=c['loads'];walk=.6 if c['n']>=1792 and (effect=='null' or c['assignment']=='no-adjacent') else .02
   for t in range(3):rr.append(dict(type='round',cell=c['cell'],position=c['position'],round=t,head_returned=True,enabled=100,running=100,counts=[8*loads+100,4*loads+20,loads,round(walk*loads),0,0]))
  return rr
 def data(self,effect='sensitive',gapped=False):
  m=self.module();return dict(mode=m.MODE,processes=3,rows=[dict(c,epoch=f'epoch-{e}') for e in range(3) for c in m.audit_process(self.records(bool(e%2),effect,gapped),bool(e%2),self.actual)])
 def test_production_space_remap_graph_and_inactive_identity(self):
  source=self.folder/'space.cpp';exe=source.with_suffix('');source.write_text(r'''#include "tlb_pfn_association_space.h"
#include <cstdio>
#include <map>
#include <set>
int main(){char file[]="/tmp/association-space-XXXXXX";int fd=mkstemp(file);if(fd<0)return 1;unlink(file);tlb_association::Space sp(fd,sysconf(_SC_PAGESIZE));std::vector<uint64_t> pfns(4096);for(unsigned i=0;i<4096;++i)pfns[i]=12345+i;std::map<unsigned,std::set<uintptr_t>> lines;unsigned count=0;for(auto c:tlb_association::cells(true)){if(!c.n)continue;auto pi=sp.remap(c,pfns);if(c.assignment=="no-adjacent")tlb_association::validate({pfns.begin(),pfns.begin()+c.n},pi,true);for(unsigned j=c.n;j<4096;++j){uint64_t a=*reinterpret_cast<volatile uintptr_t*>(sp.base+j*sp.page+64*(j%64)),b=*reinterpret_cast<volatile uintptr_t*>(sp.canonical_node(j));if(a!=b)return 3;}std::set<uintptr_t> now;for(unsigned i=0;i<c.n;++i)now.insert(sp.node(i));if(lines.count(c.n)&&lines[c.n]!=now)return 4;lines[c.n]=now;auto o=tlb_association::order(c);uintptr_t head=sp.link(c),h=head;for(unsigned j=0;j<c.n;++j){unsigned i=o[j];if(h!=sp.node(i))return 5;uintptr_t word=*reinterpret_cast<uintptr_t*>(h);if(word!=*reinterpret_cast<uintptr_t*>(sp.canonical_node(i)))return 6;h=word^tlb_association::mask;}if(h!=head)return 7;++count;}printf("%u actual remaps, same VA lines, canonical physical graph and inactive identity\n",count);}''');subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(source),'-o',str(exe)],check=True);self.assertEqual(subprocess.check_output([str(exe)],text=True),'32 actual remaps, same VA lines, canonical physical graph and inactive identity\n')
 def test_actual_plan_and_dynamic_geometry_oracle(self):
  m=self.module();m.validate_plan(self.actual)
  for (gapped,rev),rr in self.layouts.items():
   self.assertEqual(len(rr),68)
   pfns=[12345+i*(3 if gapped else 1) for i in range(4096)]
   for c,g in zip(rr[2::2],rr[3::2]):self.assertEqual(g,m.geometry(c,4294967296,pfns))
 def test_sensitive_finite_matrix_and_local_reach_are_not_physical_entries(self):
  m=self.module();a=m.analyze(self.data());self.assertEqual((a['windows'],a['verdict'],a['contiguity_control']),(297,'ASSOCIATION_SENSITIVE','CONTIGUITY_CONTROL_EXCITED'));self.assertFalse(a['physical_entries_certified']);self.assertTrue(all(c['status']=='interval' and c['interval']==[1536,1792] for c in a['curves'] if c['assignment']=='no-adjacent'))
 def test_negative_with_no_natural_adjacency_is_named_not_excited(self):
  m=self.module();a=m.analyze(self.data('null',True));self.assertEqual(a['verdict'],'ASSOCIATION_NOT_CHANGED_AT_DETECTION_SCALE');self.assertEqual(a['contiguity_control'],'NOT_EXCITED');self.assertFalse(a['hpa_attributed']);self.assertTrue(all(x['delta']==0 for c in a['comparisons'] for x in c['deltas']))
 def test_actual_raw_graph_alias_canonical_and_permutation_reject(self):
  m=self.module()
  for bad in ('missing','extra','order','word','permutation','inverse','offset','alias','canonical','swapped','huge','ir','mux','ids','typed'):
   rr=self.records();c=next(x for x in rr if x['type']=='cell' and x['n']);g=next(x for x in rr if x['type']=='geometry' and x['cell']==c['cell']);p=next(x for x in rr if x['type']=='pfn-certificate' and x['cell']==c['cell']);s=next(x for x in rr if x['type']=='round' and x['cell']==c['cell'])
   if bad=='missing':rr.pop()
   elif bad=='extra':rr.append(rr[-1])
   elif bad=='order':rr[-2:]=rr[-2:][::-1]
   elif bad=='word':next(x for x in rr if x['type']=='graph-certificate' and x['cell']==c['cell'])['stored_words'][0]^=1
   elif bad=='permutation':g['position_nodes'][0]=g['position_nodes'][1]
   elif bad=='inverse':g['node_positions'][0]+=1
   elif bad=='offset':g['offsets'][0]+=64
   elif bad=='alias':p['alias_pfns'][0]+=1
   elif bad=='canonical':p['canonical_pfns'][0]+=1
   elif bad=='swapped':p['alias_entries'][0]|=1<<62
   elif bad=='huge':next(x for x in rr if x['type']=='backing')['shmem_pmd_kb']=1
   elif bad=='ir':s['counts'][1]=3*c['loads']
   elif bad=='mux':s['running']=1
   elif bad=='ids':rr[1]['ids'][1]=rr[1]['ids'][0]
   elif bad=='typed':c['n']=True
   with self.subTest(bad=bad),self.assertRaises(ValueError):m.audit_process(rr,False,self.actual)
 def test_background_is_not_hidden_by_positive_delta(self):
  m=self.module();r=self.data()
  next(x for x in r['rows'] if x['n'])['samples'][0]['counts'][2]=0
  a=m.analyze(r);self.assertEqual(a['verdict'],'INCOMPUTABLE');self.assertFalse(a['background_passed'])
 def test_censoring_ambiguity_and_nonmonotonic_have_priority(self):
  m=self.module()
  for kind in ('left','right','ambiguous','nonmonotonic'):
   r=self.data('null')
   for row in r['rows']:
    if row['assignment']!='no-adjacent':continue
    rate=.4 if kind=='left' else .4 if kind=='right' and row['n']==3072 else .1 if kind=='ambiguous' and row['n']==1792 else .4 if kind=='nonmonotonic' and row['n'] in (1792,2560,3072) else .02
    for s in row['samples']:s['counts'][3]=round(rate*row['loads'])
   cc=[c for c in m.analyze(r)['curves'] if c['assignment']=='no-adjacent'];self.assertTrue(all(c['status']=={'left':'left-censored','right':'right-censored','ambiguous':'ambiguous','nonmonotonic':'nonmonotonic'}[kind] for c in cc))
if __name__=='__main__':unittest.main()
