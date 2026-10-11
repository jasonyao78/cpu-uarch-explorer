"""Actual producer plan/graph -> controlled PMU, never target-device evidence."""
import copy,importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class ParallelAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.folder=tempfile.TemporaryDirectory();d=Path(cls.folder.name);exe=d/'plan'
  subprocess.run(['clang++','-std=c++17','-O2','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(ROOT/'probes/diagnostic/tlb_walk_parallel.cpp'),'-o',str(exe)],check=True)
  cls.actual={key:[json.loads(l) for l in subprocess.check_output([str(exe),'--plan',*opts],text=True).splitlines()] for key,opts in [('forward',[]),('reverse',['--reverse'])]}
  src=d/'graphs.cpp';src.write_text(r'''#include "tlb_walk_parallel_layout.h"
#include <cstdio>
int main(){for(auto c:tlb_parallel::cells(false)){std::printf("{\"type\":\"geometry\",\"cell\":\"%s\",\"base\":%llu,\"chains\":[",c.id().c_str(),c.k?0x100000000ull:0ull);if(c.k){auto chains=tlb_parallel::indices(c);for(unsigned k=0;k<c.k;++k){std::printf("%s[",k?",":"");for(size_t i=0;i<chains[k].size();++i)std::printf("%s%u",i?",":"",chains[k][i]);std::printf("]");}}std::puts("]}");}}
''')
  exe=d/'graphs';subprocess.run(['clang++','-std=c++17','-O2','-I',str(ROOT/'probes/diagnostic'),str(src),'-o',str(exe)],check=True);cls.graphs={g['cell']:g for g in [json.loads(l) for l in subprocess.check_output([str(exe)],text=True).splitlines()]}
 @classmethod
 def tearDownClass(cls):cls.folder.cleanup()
 def module(self):
  self.assertTrue((ROOT/'tools/diagnostic/tlb_walk_parallel_analysis.py').exists(),'parallel consumer missing');return importlib.import_module('tools.diagnostic.tlb_walk_parallel_analysis')
 def records(self,reverse=False):
  selected=self.actual['reverse' if reverse else 'forward'];rows=[copy.deepcopy(selected[0]),dict(type='pmu',ids=[1,2,3,4,5,6])]
  for c in selected[1:]:
   rows.extend([copy.deepcopy(c),copy.deepcopy(self.graphs[c['cell']])]);rows.extend(dict(type='backing',cell=c['cell'],stage=s,base_page_bytes=4096,anon_huge_kb=0) for s in ('before','after'))
   for t in range(3):
    n=c['loads'];k=c['k'];high=c['layout']=='high';counts=[(8*n//k+100) if k else 100,(n+2*n//k+20) if k else 20,n//100, n//1000,n//2 if high else 0,10*n if high else 0]
    rows.append(dict(type='round',cell=c['cell'],position=c['position'],round=t,head_returned=True,enabled=100,running=100,counts=counts))
  return rows
 def data(self):
  m=self.module();return dict(mode=m.MODE,processes=5,rows=[dict(r,epoch=f'epoch-{e}') for e in range(5) for r in m.audit_process(self.records(bool(e%2)),bool(e%2),self.actual)])
 def test_actual_graph_plan_windows_and_paired_ratios(self):
  m=self.module();m.validate_plan(self.actual);a=m.analyze(self.data());self.assertEqual((a['windows'],len(a['points'])),(495,32));self.assertEqual(a['qualification'],'qualified-effective-occupancy');self.assertFalse(a['physical_queue_certified'])
  point=next(p for p in a['points'] if p['scope']=='total' and p['layout']=='high' and p['k']==8 and p['loads']==1048576);self.assertGreater(point['ratios']['occupancy'],1)
  low=next(p for p in a['points'] if p['layout']=='low');self.assertIsNone(low['ratios']['residence_cycles']);self.assertEqual(low['walk_state'],'walk-inactive')
 def test_every_production_boundary_rejects(self):
  m=self.module();rows=self.records()
  for kind in ('missing','duplicate','order','cell','typed-k','graph','id-duplicate','id-bool','mux','count-bool','head','backing','ir'):
   rr=copy.deepcopy(rows)
   if kind=='missing':rr.pop()
   elif kind=='duplicate':rr.append(rr[-1])
   elif kind=='order':rr[-2:]=rr[-2:][::-1]
   elif kind=='cell':rr[9]['cell']='conflict'
   elif kind=='typed-k':rr[9]['k']=True
   elif kind=='graph':rr[10]['chains'][0][0]=rr[10]['chains'][0][1]
   elif kind=='id-duplicate':rr[1]['ids'][1]=rr[1]['ids'][0]
   elif kind=='id-bool':rr[1]['ids'][0]=True
   elif kind=='mux':rr[13]['running']=99
   elif kind=='count-bool':rr[13]['counts'][0]=True
   elif kind=='head':rr[13]['head_returned']=False
   elif kind=='backing':rr[11]['anon_huge_kb']=1
   elif kind=='ir':rr[13]['counts'][1]=1
   with self.subTest(kind=kind),self.assertRaises(ValueError):m.audit_process(rr,False,self.actual)
 def test_sum_ratios_background_and_inactive_scope_are_not_rescued(self):
  m=self.module();r=self.data();cell=next(c for c in r['rows'] if c['epoch']=='epoch-0' and c['layout']=='high' and c['k']==1 and c['loads']==1048576);cell['samples'][0]['counts'][0]*=10;a=m.analyze(r);point=next(p for p in a['points'] if p['cell']==cell['cell']);samples=[s for c in r['rows'] if c['cell']==cell['cell'] for s in c['samples']];self.assertEqual(point['ratios']['occupancy'],sum(s['counts'][5] for s in samples)/sum(s['counts'][0] for s in samples))
  for kind in ('high-inactive','low-active','A-not-covarying','background'):
   rr=self.data()
   for c in rr['rows']:
    if c['epoch']!='epoch-4':continue
    for s in c['samples']:
     if kind=='high-inactive' and c['layout']=='high':s['counts'][4]=s['counts'][5]=0
     if kind=='A-not-covarying' and c['layout']=='low':s['counts'][5]=20*c['loads']
     if kind=='low-active' and c['layout']=='low':s['counts'][4]=c['loads']//2;s['counts'][5]=10*c['loads']
     if kind=='background' and c['layout']=='empty':s['counts'][0]=100000000;s['counts'][4]=3;s['counts'][5]=10
   a=m.analyze(rr);self.assertEqual(a['qualification'],'not-qualified',kind)
   if kind=='background':self.assertTrue(any(p['corrected_counts'][0]<0 for p in a['window_ratios']))
if __name__=='__main__':unittest.main()
