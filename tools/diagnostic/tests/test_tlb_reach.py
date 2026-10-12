"""Native producer/layout/graph -> consumer; external counters are synthetic."""
import copy,importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class ReachAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.folder=tempfile.TemporaryDirectory();d=Path(cls.folder.name);exe=d/'reach'
  subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(ROOT/'probes/diagnostic/tlb_balanced_reach.cpp'),'-o',str(exe)],check=True)
  cls.actual={key:[json.loads(l) for l in subprocess.check_output([str(exe),'--plan',*opts],text=True).splitlines()] for key,opts in [('forward',[]),('reverse',['--reverse'])]}
  cls.layouts={key:[json.loads(l) for l in subprocess.check_output([str(exe),'--layout','4294975488',*opts],text=True).splitlines()] for key,opts in [('forward',[]),('reverse',['--reverse'])]}
  cls.exe=exe
 @classmethod
 def tearDownClass(cls):cls.folder.cleanup()
 def module(self):return importlib.import_module('tools.diagnostic.tlb_reach_analysis')
 def records(self,reverse=False):
  layout=copy.deepcopy(self.layouts['reverse' if reverse else 'forward']);rows=[layout[0],dict(type='pmu',ids=[1,2,3,4,5,6]),layout[1]]
  for i in range(2,len(layout),2):
   c,g=layout[i:i+2];rows.extend([c,g]);rows.extend(dict(type='backing',cell=c['cell'],stage=t,base_page_bytes=4096,anon_huge_kb=0) for t in ('before','after'))
   for t in range(3):
    n=c['loads'];walk=0 if c['n']<1536 else .5 if c['shape']=='dense' else .75
    rows.append(dict(type='round',cell=c['cell'],position=c['position'],round=t,head_returned=True,enabled=100,running=100,counts=[8*n+100,3*n+20,n,round(walk*n),n,round(walk*n)]))
  return rows
 def data(self):
  m=self.module();return dict(mode=m.MODE,processes=5,rows=[dict(r,epoch=f'epoch-{e}') for e in range(5) for r in m.audit_process(self.records(bool(e%2)),bool(e%2),self.actual)])
 def test_real_plan_layout_matches_independent_oracle(self):
  m=self.module();m.validate_plan(self.actual)
  for reverse in (False,True):
   rr=self.layouts['reverse' if reverse else 'forward'];self.assertEqual(len(rr),112);self.assertEqual(rr[1],m.mapping(4294975488))
   for c,g in zip(rr[2::2],rr[3::2]):self.assertEqual(g,m.geometry(c,4294975488));self.assertEqual(sum(g['vpn_low8_hist']),c['n']);self.assertEqual(len(set(g['page_ids'])),c['n'])
  for n in m.GRID:
   gs=[m.geometry(next(c for c in m.plan(False)[1:] if c['shape']==s and c['n']==n),4294975488) for s in m.SHAPES];self.assertTrue(all(g['vpn_low8_hist']==gs[0]['vpn_low8_hist'] for g in gs));self.assertTrue(all(sorted(g['offsets'])==sorted(gs[0]['offsets']) for g in gs))
 def test_real_graph_all_nodes_and_closed_walk(self):
  src=Path(self.folder.name)/'graph.cpp';exe=src.with_suffix('');src.write_text(r"""#include "tlb_balanced_reach_layout.h"
#include <sys/mman.h>
#include <unistd.h>
#include <cstdio>
int main(){size_t bytes=1048576ull*4096;char* base=static_cast<char*>(mmap(nullptr,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0));if(base==MAP_FAILED)return 1;unsigned tested=0;for(auto c:tlb_reach::cells(false)){if(!c.n)continue;auto p=tlb_reach::pages(c.shape,c.n);auto o=tlb_reach::order(c);uintptr_t h=tlb_reach::link(base,c,p,o),node=h;for(unsigned i=0;i<c.n;++i){unsigned index=o[i];if(node!=reinterpret_cast<uintptr_t>(base)+uint64_t(p[index])*4096+tlb_reach::offset(p[index]))return 2;node=*reinterpret_cast<uintptr_t*>(node);}if(node!=h)return 3;for(unsigned i=0;i<c.loads;++i)node=*reinterpret_cast<uintptr_t*>(node);if(node!=h)return 4;++tested;}munmap(base,bytes);std::printf("%u\n",tested);}""")
  subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/diagnostic'),str(src),'-o',str(exe)],check=True);self.assertEqual(subprocess.check_output([str(exe)],text=True),'54\n')
 def test_every_actual_process_boundary_rejects(self):
  m=self.module();rows=self.records()
  for kind in ('missing','duplicate','order','cell','typed-n','pages','visit-order','offset','mapping','hpa','parent','hist','id','mux','count','head','backing','ir'):
   rr=copy.deepcopy(rows)
   if kind=='missing':rr.pop()
   elif kind=='duplicate':rr.append(rr[-1])
   elif kind=='order':rr[-2:]=rr[-2:][::-1]
   elif kind=='cell':rr[10]['cell']='bad'
   elif kind=='typed-n':rr[10]['n']=True
   elif kind=='pages':rr[11]['page_ids'][0]+=1
   elif kind=='visit-order':rr[11]['order_indices'][0]=rr[11]['order_indices'][1]
   elif kind=='offset':rr[11]['offsets'][0]=64
   elif kind=='mapping':rr[2]['prefaulted_page_ids'].pop()
   elif kind=='hpa':rr[2]['hpa_state']='enabled'
   elif kind=='parent':rr[11]['l3_parent_ids'].pop()
   elif kind=='hist':rr[11]['vpn_low8_hist'][0]+=1
   elif kind=='id':rr[1]['ids'][1]=rr[1]['ids'][0]
   elif kind=='mux':rr[14]['running']=99
   elif kind=='count':rr[14]['counts'][5]=True
   elif kind=='head':rr[14]['head_returned']=False
   elif kind=='backing':rr[12]['anon_huge_kb']=1
   elif kind=='ir':rr[14]['counts'][1]=1
   with self.subTest(kind=kind),self.assertRaises(ValueError):m.audit_process(rr,False,self.actual)
 def test_finite_curves_replication_and_sum_ratios(self):
  a=self.module().analyze(self.data());self.assertEqual((a['windows'],a['verdict'],len(a['curves'])),(825,'GEOMETRY_SENSITIVE',30));self.assertTrue(all(c['interval']==[1280,1536] for c in a['curves']));self.assertTrue(all(c['status']=='replicated' for c in a['reach']));self.assertFalse(a['physical_entries_certified'])
  r=self.data();r['rows'][2]['samples'][0]['counts'][0]*=10;a=self.module().analyze(r);c=r['rows'][2];p=next(p for p in a['points'] if p['cell']==c['cell']);ss=[s for row in r['rows'] if row['cell']==c['cell'] for s in row['samples']];self.assertEqual(p['cycles_per_load'],sum(s['counts'][0] for s in ss)/(15*c['loads']))
 def test_ambiguity_nonmonotone_and_both_censors(self):
  m=self.module()
  for kind in ('left','left-nonmonotone','right','none','straddle'):
   r=self.data()
   for c in r['rows']:
    if c['shape']=='spaced':
     high=kind=='left' or (kind=='left-nonmonotone' and c['n']!=1024) or (kind=='right' and c['n']==3072)
     for s in c['samples']:s['counts'][5]=c['loads']*int(high)
     if kind=='straddle' and c['n']==1280:c['samples'][0]['counts'][5]=c['loads']
   a=m.analyze(r);cs=[c for c in a['curves'] if c['shape']=='spaced'];expected=dict(left='left-censored',**{'left-nonmonotone':'ambiguous','right':'right-censored','none':'no-crossing-through3072','straddle':'ambiguous'})[kind];self.assertTrue(all(c['status']==expected for c in cs))
 def test_translation_pressure_floor_and_negative_correction_retained(self):
  m=self.module()
  for kind in ('pressure','floor'):
   r=self.data()
   for c in r['rows']:
    if c['epoch']=='epoch-4':
     for s in c['samples']:
      if kind=='pressure' and c['n']==1536:s['counts'][2]=0
      if kind=='floor' and not c['n']:s['counts'][0]=100000000
   a=m.analyze(r);self.assertEqual(a['verdict'],'INCONCLUSIVE');self.assertTrue(all(c['status']=='INCOMPUTABLE' for c in a['curves'] if c['epoch']==4));self.assertFalse(any(p['replicated'] for p in a['comparisons']))
   if kind=='floor':self.assertTrue(any(w['corrected_counts'][0]<0 for w in a['window_ratios']))
 def test_no_difference_and_epoch_specific_interval(self):
  m=self.module();r=self.data()
  for c in r['rows']:
   for s in c['samples']:s['counts'][5]=round(.5*c['loads']) if c['n']>=1536 else 0
  a=m.analyze(r);self.assertEqual(a['verdict'],'NO_DIFFERENCE_DETECTED')
  for c in r['rows']:
   if c['epoch']=='epoch-4' and c['shape']=='dense' and c['n']==1280:
    for s in c['samples']:s['counts'][5]=c['loads']
  a=m.analyze(r);self.assertEqual(next(c for c in a['reach'] if c['shape']=='dense')['status'],'heterogeneous')
 def test_usage_types_and_native_run_refused(self):
  for args in (['--layout','-1'],['--layout','True'],['--layout','4097'],['--run'],['--plan','--bad']):
   p=subprocess.run([str(self.exe),*args],capture_output=True,text=True);self.assertNotEqual(p.returncode,0)
if __name__=='__main__':unittest.main()
