"""Actual C++ plan and host shared-FD graphs; external PMU/PFN values are synthetic."""
import copy,importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class FullReprAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  source=ROOT/'probes/diagnostic/tlb_full_repr.cpp'
  if not source.exists():raise AssertionError('representation producer missing')
  cls.folder=tempfile.TemporaryDirectory();d=Path(cls.folder.name);exe=d/'repr';subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(source),'-o',str(exe)],check=True);cls.exe=exe
  cls.actual={k:[json.loads(l) for l in subprocess.check_output([str(exe),'--plan',*opt],text=True).splitlines()] for k,opt in [('forward',[]),('reverse',['--reverse'])]}
  cls.layouts={k:[json.loads(l) for l in subprocess.check_output([str(exe),'--layout','4294967296',*opt],text=True).splitlines()] for k,opt in [('forward',[]),('reverse',['--reverse'])]}
 @classmethod
 def tearDownClass(cls):cls.folder.cleanup()
 def module(self):return importlib.import_module('tools.diagnostic.tlb_full_repr_analysis')
 def records(self,reverse=False,effect='sensitive'):
  m=self.module();layout=copy.deepcopy(self.layouts['reverse' if reverse else 'forward']);mapping=layout[1];mapping.update(canonical_base=85899345920,canonical_pfns=list(range(12345,14905)));mapping['canonical_entries']=[(1<<63)|(1<<56)|v for v in mapping['canonical_pfns']];rr=[layout[0],dict(type='pmu',ids=list(range(1,7))),mapping]
  for i in range(2,len(layout),2):
   c,g=layout[i:i+2];rr.extend([c,g]);base=mapping['arena_bases'][m.SHAPES.index(c['shape'])] if c['n'] else 0
   for stage in ('before','after'):
    rr.extend([dict(type='backing',cell=c['cell'],stage=stage,kernel_page_kb=4,mmu_page_kb=4,anon_huge_kb=0,shmem_pmd_kb=0,file_pmd_kb=0),dict(type='pfn-certificate',cell=c['cell'],stage=stage,alias_pfns=mapping['canonical_pfns'][:c['n']],pagemap_entries=mapping['canonical_entries'][:c['n']]),dict(m.graph(c,base),type='graph-certificate',stage=stage)])
   n=c['loads'];walk=0 if c['n']<1792 or effect=='no-base' else .6 if c['shape']!='dense' else .4 if c['representation']=='xor-full' and effect=='sensitive' else .05
   for t in range(3):rr.append(dict(type='round',cell=c['cell'],position=c['position'],round=t,head_returned=True,enabled=100,running=100,counts=[8*n+100,4*n+20,n,round(walk*n),0,0]))
  return rr
 def data(self,effect='sensitive'):
  m=self.module();return dict(mode=m.MODE,processes=3,rows=[dict(c,epoch=f'epoch-{e}') for e in range(3) for c in m.audit_process(self.records(bool(e%2),effect),bool(e%2),self.actual)])
 def test_actual_plan_layout_oracle(self):
  m=self.module();m.validate_plan(self.actual)
  for rev in (False,True):
   rr=self.layouts['reverse' if rev else 'forward'];self.assertEqual(len(rr),112);self.assertEqual(rr[1],m.layout_mapping(4294967296))
   for c,g in zip(rr[2::2],rr[3::2]):self.assertEqual(g,m.geometry(c,rr[1]['arena_bases']))
 def test_actual_fiftyfour_shared_fd_graphs_decode_and_keep_demand_order(self):
  src=Path(self.folder.name)/'graphs.cpp';exe=src.with_suffix('');src.write_text(r'''#include "tlb_full_repr_layout.h"
#include <cstdio>
int main(){char name[]="/tmp/repr-test-XXXXXX";int fd=mkstemp(name);if(fd<0)return 1;unlink(name);tlb_alias::Space sp(fd,sysconf(_SC_PAGESIZE));unsigned count=0;for(auto c:tlb_fullrepr::cells(false)){if(!c.trace.n)continue;auto o=tlb_reach::order(c.trace);uintptr_t h=tlb_fullrepr::link(sp,c),node=h;for(unsigned i=0;i<c.trace.n;++i){unsigned k=o[i],next=o[(i+1)%c.trace.n];if(node!=sp.node(c.trace.shape,k))return 2;uintptr_t stored=*reinterpret_cast<uintptr_t*>(sp.canonical_node(k));if((stored^c.mask)!=sp.node(c.trace.shape,next))return 3;if(c.representation=="xor-full")for(unsigned width:{39,48,56}){uint64_t mask=(UINT64_C(1)<<width)-1,decoded=sp.node(c.trace.shape,next);if((stored&mask)==(decoded&mask)||(stored&mask&~UINT64_C(63))==(decoded&mask&~UINT64_C(63)))return 7;}for(const char* shape:{"dense","spaced","balanced-random"})if(*reinterpret_cast<uintptr_t*>(sp.node(shape,k))!=stored)return 4;node=*reinterpret_cast<uintptr_t*>(node)^c.mask;}if(node!=h)return 5;for(unsigned i=0;i<c.trace.loads;++i)node=*reinterpret_cast<uintptr_t*>(node)^c.mask;if(node!=h)return 6;++count;}std::printf("%u\n",count);}''');subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(src),'-o',str(exe)],check=True);self.assertEqual(subprocess.check_output([str(exe)],text=True),'54\n')
 def test_exact_raw_graph_pfn_and_counts_reject(self):
  m=self.module()
  for kind in ('missing','extra','order','word-before','word-after','head','mask','pfn','wire','huge','ir','mux','ids'):
   rr=self.records();c=next(x for x in rr if x['type']=='cell' and x['n']);graphs=[x for x in rr if x['type']=='graph-certificate' and x['cell']==c['cell']];cert=next(x for x in rr if x['type']=='pfn-certificate' and x['cell']==c['cell']);sample=next(x for x in rr if x['type']=='round' and x['cell']==c['cell'])
   if kind=='missing':rr.pop()
   elif kind=='extra':rr.append(rr[-1])
   elif kind=='order':rr[-2:]=rr[-2:][::-1]
   elif kind.startswith('word'):graphs[kind.endswith('after')]['stored_words'][0]^=1
   elif kind=='head':graphs[0]['head']+=64
   elif kind=='mask':c['mask']=True
   elif kind=='pfn':cert['alias_pfns'][0]+=1
   elif kind=='wire':cert['pagemap_entries'][0]|=1<<62
   elif kind=='huge':next(x for x in rr if x['type']=='backing')['file_pmd_kb']=1
   elif kind=='ir':sample['counts'][1]=3*c['loads']
   elif kind=='mux':sample['running']=1
   elif kind=='ids':rr[1]['ids'][1]=rr[1]['ids'][0]
   with self.subTest(kind=kind),self.assertRaises(ValueError):m.audit_process(rr,False,self.actual)
 def test_sensitive_did_and_zero_prefetch_not_an_absence_certificate(self):
  m=self.module();a=m.analyze(self.data());self.assertEqual((a['windows'],a['verdict']),(495,'GEOMETRY_CONTRAST_REPRESENTATION_SENSITIVE'));self.assertEqual(a['prefetch_status'],'NO_PREFETCH_COUNTS_IN_MATRIX');self.assertFalse(a['physical_entries_certified']);self.assertFalse(a['dmp_attributed']);self.assertNotIn('12345',json.dumps(self.data()))
 def test_null_and_baseline_not_replicated(self):
  m=self.module();self.assertEqual(m.analyze(self.data('no-change'))['verdict'],'GEOMETRY_CONTRAST_NOT_CHANGED_AT_DETECTION_SCALE');self.assertEqual(m.analyze(self.data('no-base'))['verdict'],'BASE_GEOMETRY_NOT_REPLICATED')
 def test_global_failure_and_inconsistent_signed_contrasts(self):
  m=self.module();r=self.data()
  for c in r['rows']:
   if c['epoch']=='epoch-1' and c['representation']=='xor-full' and c['shape']=='dense' and c['n']>=1792:
    for s in c['samples']:s['counts'][3]=round(.05*c['loads'])
  self.assertEqual(m.analyze(r)['verdict'],'INCONCLUSIVE')
  for c in r['rows']:
   if c['n']==0:
    for s in c['samples']:s['counts'][0]=100000000
  self.assertFalse(m.analyze(r)['background_passed'])
 def test_every_auxiliary_representation_change_is_exported(self):
  a=self.module().analyze(self.data());self.assertEqual(len(a['representation_changes']),18)
  self.assertEqual({p['representation'] for p in a['representation_changes']},{'xor-high','xor-full'})
  self.assertEqual(len(a['auxiliary_comparisons']),12)
  for c in a['auxiliary_comparisons']:
   if c['second']=='xor-high':self.assertTrue(all(x['delta']==0 for x in c['deltas']))
 def test_impossible_uint64_wire_values_rejected(self):
  m=self.module()
  for field in ('event-id','time'):
   rr=self.records()
   if field=='event-id':rr[1]['ids'][0]=2**64
   else:rr[-1]['enabled']=rr[-1]['running']=2**64
   with self.subTest(field=field),self.assertRaises(ValueError):m.audit_process(rr,False,self.actual)
 def test_summary_certificate_and_native_bad_usage(self):
  r=self.data();r['rows'][1]['stored_graph_verified']=True
  with self.assertRaises(ValueError):self.module().analyze(r)
  for args in (['--run'],['--layout','4096'],['--layout','True'],['--plan','--bad']):self.assertNotEqual(subprocess.run([str(self.exe),*args],capture_output=True).returncode,0)
if __name__=='__main__':unittest.main()
