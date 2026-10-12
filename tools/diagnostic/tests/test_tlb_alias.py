"""Real shared-file aliases at host granule; never target 4 KiB PMU evidence."""
import copy,importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class AliasAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.folder=tempfile.TemporaryDirectory();d=Path(cls.folder.name);exe=d/'alias';subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(ROOT/'probes/diagnostic/tlb_shared_alias.cpp'),'-o',str(exe)],check=True);cls.exe=exe
  cls.actual={key:[json.loads(l) for l in subprocess.check_output([str(exe),'--plan',*opts],text=True).splitlines()] for key,opts in [('forward',[]),('reverse',['--reverse'])]}
  cls.layouts={key:[json.loads(l) for l in subprocess.check_output([str(exe),'--layout','4294967296',*opts],text=True).splitlines()] for key,opts in [('forward',[]),('reverse',['--reverse'])]}
 @classmethod
 def tearDownClass(cls):cls.folder.cleanup()
 def module(self):return importlib.import_module('tools.diagnostic.tlb_alias_analysis')
 def records(self,reverse=False):
  layout=copy.deepcopy(self.layouts['reverse' if reverse else 'forward']);mapping=layout[1];mapping['canonical_base']=85899345920;mapping['canonical_pfns']=list(range(12345,12345+2560));mapping['canonical_entries']=[(1<<63)|(1<<56)|v for v in mapping['canonical_pfns']];rows=[layout[0],dict(type='pmu',ids=[1,2,3,4,5,6]),mapping]
  for i in range(2,len(layout),2):
   c,g=layout[i:i+2];rows.extend([c,g])
   for stage in ('before','after'):
    rows.append(dict(type='backing',cell=c['cell'],stage=stage,kernel_page_kb=4,mmu_page_kb=4,anon_huge_kb=0,shmem_pmd_kb=0,file_pmd_kb=0));rows.append(dict(type='pfn-certificate',cell=c['cell'],stage=stage,alias_pfns=mapping['canonical_pfns'][:c['n']],pagemap_entries=mapping['canonical_entries'][:c['n']]))
   for t in range(3):
    n=c['loads'];walk=0 if c['n']<1792 else .5 if c['shape']=='dense' else .75;rows.append(dict(type='round',cell=c['cell'],position=c['position'],round=t,head_returned=True,enabled=100,running=100,counts=[8*n+100,3*n+20,n,round(walk*n),n,round(walk*n)]))
  return rows
 def data(self):
  m=self.module();return dict(mode=m.MODE,processes=3,rows=[dict(r,epoch=f'epoch-{e}') for e in range(3) for r in m.audit_process(self.records(bool(e%2)),bool(e%2),self.actual)])
 def test_real_plan_and_layout_match_oracle(self):
  m=self.module();m.validate_plan(self.actual)
  for reverse in (False,True):
   rr=self.layouts['reverse' if reverse else 'forward'];self.assertEqual(len(rr),64);self.assertEqual(rr[1],m.layout_mapping(4294967296))
   for c,g in zip(rr[2::2],rr[3::2]):self.assertEqual(g,m.geometry(c,rr[1]['arena_bases']))
 def test_all_thirty_graphs_really_alias_same_file_at_host_page_size(self):
  src=Path(self.folder.name)/'shared.cpp';exe=src.with_suffix('');src.write_text(r'''#include "tlb_shared_alias_layout.h"
#include <cstdio>
int main(){char name[]="/tmp/alias-test-XXXXXX";int fd=mkstemp(name);if(fd<0)return 1;unlink(name);tlb_alias::Space space(fd,sysconf(_SC_PAGESIZE));unsigned count=0;for(auto c:tlb_alias::cells(false)){if(!c.n)continue;auto pp=tlb_reach::pages(c.shape,c.n);auto oo=tlb_reach::order(c);uintptr_t h=space.link(c),node=h;for(unsigned i=0;i<c.n;++i){unsigned index=oo[i],next=oo[(i+1)%c.n];if(node!=space.node(c.shape,index)||*reinterpret_cast<uintptr_t*>(space.canonical_node(index))!=space.node(c.shape,next))return 2;for(const char* sh:{"dense","spaced","balanced-random"})if(*reinterpret_cast<uintptr_t*>(space.node(sh,index))!=space.node(c.shape,next))return 3;node=*reinterpret_cast<uintptr_t*>(node);}if(node!=h)return 4;for(unsigned i=0;i<c.loads;++i)node=*reinterpret_cast<uintptr_t*>(node);if(node!=h)return 5;++count;}std::printf("%u\n",count);}''');subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(src),'-o',str(exe)],check=True);self.assertEqual(subprocess.check_output([str(exe)],text=True),'30\n')
 def test_pfn_binding_and_backing_each_stage_reject(self):
  m=self.module()
  for kind in ('missing','extra','typed-n','canonical-zero','canonical-duplicate','pfn-before','pfn-after','pfn-bool','wire-pfn','wire-present','wire-swap','wire-type','canonical-wire','huge','shmem','file','mmu','alias-base','geometry','mux','head','ir'):
   rr=self.records()
   if kind=='missing':rr.pop()
   elif kind=='extra':rr.append(rr[-1])
   elif kind=='typed-n':rr[12]['n']=True
   elif kind=='canonical-zero':rr[2]['canonical_pfns'][0]=0
   elif kind=='canonical-duplicate':rr[2]['canonical_pfns'][1]=rr[2]['canonical_pfns'][0]
   elif kind=='pfn-before':rr[15]['alias_pfns'][0]+=1
   elif kind=='pfn-after':rr[17]['alias_pfns'][0]+=1
   elif kind=='pfn-bool':rr[15]['alias_pfns'][0]=True
   elif kind=='wire-pfn':rr[15]['pagemap_entries'][0]+=1
   elif kind=='wire-present':rr[15]['pagemap_entries'][0]&=~(1<<63)
   elif kind=='wire-swap':rr[17]['pagemap_entries'][0]|=1<<62
   elif kind=='wire-type':rr[17]['pagemap_entries'][0]=True
   elif kind=='canonical-wire':rr[2]['canonical_entries'][0]&=~(1<<63)
   elif kind=='huge':rr[14]['anon_huge_kb']=1
   elif kind=='shmem':rr[14]['shmem_pmd_kb']=1
   elif kind=='file':rr[14]['file_pmd_kb']=1
   elif kind=='mmu':rr[14]['mmu_page_kb']=16
   elif kind=='alias-base':rr[2]['arena_bases'][0]+=4096
   elif kind=='geometry':rr[13]['page_ids'][0]+=1
   elif kind=='mux':rr[18]['running']=1
   elif kind=='head':rr[18]['head_returned']=False
   elif kind=='ir':rr[18]['counts'][1]=1
   with self.subTest(kind=kind),self.assertRaises(ValueError):m.audit_process(rr,False,self.actual)
 def test_real_rows_pfn_summary_ratios_and_verdict(self):
  m=self.module();a=m.analyze(self.data());self.assertEqual((a['windows'],a['verdict']),(279,'GEOMETRY_SENSITIVE_WITH_MATCHED_DATA_PFNS'));self.assertFalse(a['physical_entries_certified']);self.assertEqual(len(a['comparisons']),10);self.assertNotIn('12345',json.dumps(self.data()))
 def test_no_difference_and_floor_failure(self):
  m=self.module();r=self.data()
  for c in r['rows']:
   for s in c['samples']:s['counts'][5]=0
  self.assertEqual(m.analyze(r)['verdict'],'NO_DIFFERENCE_DETECTED')
  for c in r['rows']:
   if c['epoch']=='epoch-2' and c['n']==0:
    for s in c['samples']:s['counts'][0]=100000000
  a=m.analyze(r);self.assertEqual(a['verdict'],'INCONCLUSIVE');self.assertFalse(any(c['replicated'] for c in a['comparisons']))
 def test_native_usage_refuses_measurement(self):
  for args in (['--run'],['--layout','4096'],['--layout','True'],['--plan','--bad']):self.assertNotEqual(subprocess.run([str(self.exe),*args],capture_output=True).returncode,0)
if __name__=='__main__':unittest.main()
