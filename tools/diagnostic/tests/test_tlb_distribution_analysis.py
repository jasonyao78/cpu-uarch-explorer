"""Actual producer plan/graph -> controlled PMU, never target-device evidence."""
import copy,importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class DistributionAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.folder=tempfile.TemporaryDirectory();d=Path(cls.folder.name);exe=d/'plan'
  subprocess.run(['clang++','-std=c++17','-O2','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(ROOT/'probes/diagnostic/tlb_page_distribution.cpp'),'-o',str(exe)],check=True)
  cls.actual={key:[json.loads(l) for l in subprocess.check_output([str(exe),'--plan',*opts],text=True).splitlines()] for key,opts in [('forward',[]),('reverse',['--reverse'])]}
  src=d/'graphs.cpp';src.write_text(r'''#include "tlb_page_distribution_layout.h"
#include <cstdio>
void arr(const std::vector<unsigned>& a){std::printf("[");for(size_t i=0;i<a.size();++i)std::printf("%s%u",i?",":"",a[i]);std::printf("]");}
int main(){for(auto c:tlb_distribution::cells(false)){std::vector<unsigned> p,o,offset;if(c.n){p=tlb_distribution::pages(c.shape,c.n);o=tlb_distribution::order(c);for(unsigned x:p)offset.push_back(tlb_distribution::offset(c,x));}std::printf("{\"type\":\"geometry\",\"cell\":\"%s\",\"page_ids\":",c.id().c_str());arr(p);std::printf(",\"order_indices\":");arr(o);std::printf(",\"offsets\":");arr(offset);std::puts("}");}}
''')
  exe=d/'graphs';subprocess.run(['clang++','-std=c++17','-O2','-I',str(ROOT/'probes/diagnostic'),str(src),'-o',str(exe)],check=True);cls.graphs={g['cell']:g for g in [json.loads(l) for l in subprocess.check_output([str(exe)],text=True).splitlines()]}
 @classmethod
 def tearDownClass(cls):cls.folder.cleanup()
 def module(self):
  self.assertTrue((ROOT/'tools/diagnostic/tlb_distribution_analysis.py').exists(),'distribution consumer missing');return importlib.import_module('tools.diagnostic.tlb_distribution_analysis')
 def records(self,reverse=False):
  selected=self.actual['reverse' if reverse else 'forward'];union=sorted({p for g in self.graphs.values() for p in g['page_ids']});mapping=dict(type='mapping',base=4294967296,pool_pages=262144,hpa_state='UNKNOWN',pte_cont_state='UNKNOWN',prefaulted_page_ids=union);rows=[copy.deepcopy(selected[0]),dict(type='pmu',ids=[1,2,3,4,5,6]),mapping]
  for c in selected[1:]:
   rows.extend([copy.deepcopy(c),copy.deepcopy(self.graphs[c['cell']])]);rows.extend(dict(type='backing',cell=c['cell'],stage=t,base_page_bytes=4096,anon_huge_kb=0) for t in ('before','after'))
   for t in range(3):
    n=c['loads'];p=0 if not c['n'] or c['n']<=96 else .1 if c['shape']=='contiguous' else 1;counts=[8*n+100,3*n+20,round(p*n),round((.7 if c['offset']=='constant' else .001)*n),0,0];rows.append(dict(type='round',cell=c['cell'],position=c['position'],round=t,head_returned=True,enabled=100,running=100,counts=counts))
  return rows
 def data(self):
  m=self.module();return dict(mode=m.MODE,processes=5,rows=[dict(r,epoch=f'epoch-{e}') for e in range(5) for r in m.audit_process(self.records(bool(e%2)),bool(e%2),self.actual)])
 def test_actual_graph_plan_ratios_and_operational_interval(self):
  m=self.module();m.validate_plan(self.actual);a=m.analyze(self.data());self.assertEqual((a['windows'],a['verdict']),(2175,'DISTRIBUTION_SENSITIVE'));self.assertFalse(a['physical_entries_certified']);self.assertEqual(len(a['comparisons']),24);curve=next(c for c in a['curves'] if c['epoch']==0 and c['shape']=='sparse' and c['offset']=='rotated' and c['order']=='random');self.assertEqual((curve['status'],curve['interval']),('interval',[96,112]))
 def test_every_production_boundary_rejects(self):
  m=self.module();rows=self.records()
  for kind in ('missing','duplicate','order','cell','typed-n','pages','visit-order','offset','mapping','hpa','id-duplicate','mux','count-bool','head','backing','ir'):
   rr=copy.deepcopy(rows)
   if kind=='missing':rr.pop()
   elif kind=='duplicate':rr.append(rr[-1])
   elif kind=='order':rr[-2:]=rr[-2:][::-1]
   elif kind=='cell':rr[10]['cell']='conflict'
   elif kind=='typed-n':rr[10]['n']=True
   elif kind=='pages':rr[11]['page_ids'][0]+=1
   elif kind=='visit-order':rr[11]['order_indices'][0]=rr[11]['order_indices'][1]
   elif kind=='offset':rr[11]['offsets'][0]=64
   elif kind=='mapping':rr[2]['prefaulted_page_ids'].pop()
   elif kind=='hpa':rr[2]['hpa_state']='enabled'
   elif kind=='id-duplicate':rr[1]['ids'][1]=rr[1]['ids'][0]
   elif kind=='mux':rr[14]['running']=99
   elif kind=='count-bool':rr[14]['counts'][0]=True
   elif kind=='head':rr[14]['head_returned']=False
   elif kind=='backing':rr[12]['anon_huge_kb']=1
   elif kind=='ir':rr[14]['counts'][1]=1
   with self.subTest(kind=kind),self.assertRaises(ValueError):m.audit_process(rr,False,self.actual)
 def test_diff_detection_noise_background_and_sum_ratios(self):
  m=self.module();r=self.data();cell=next(c for c in r['rows'] if c['epoch']=='epoch-0' and c['shape']=='sparse' and c['n']==112);cell['samples'][0]['counts'][0]*=10;a=m.analyze(r);point=next(p for p in a['points'] if p['cell']==cell['cell']);ss=[s for c in r['rows'] if c['cell']==cell['cell'] for s in c['samples']];self.assertEqual(point['cycles_per_load'],sum(s['counts'][0] for s in ss)/(15*cell['loads']))
  for kind in ('no-diff','one-map-only','I-noise','floor'):
   rr=self.data()
   if kind in ('no-diff','one-map-only'):
    for c in rr['rows']:
     for s in c['samples']:s['counts'][2]=round(.1*c['loads']) if c['n'] else 0
    if kind=='one-map-only':
     for c in rr['rows']:
      if c['epoch']=='epoch-4' and c['shape']=='sparse' and c['n']==112:
       for s in c['samples']:s['counts'][2]=c['loads']
   else:
    for c in rr['rows']:
     if c['epoch']=='epoch-4':
      for s in c['samples']:
       if kind=='I-noise' and c['n']==112:s['counts'][5]=c['loads']
       if kind=='floor' and not c['n']:s['counts'][0]=100000000
   a=m.analyze(rr);self.assertEqual(a['verdict'],'NO_DIFFERENCE_DETECTED' if kind=='no-diff' else 'INCONCLUSIVE',kind)
   if kind=='floor':
    self.assertTrue(any(w['corrected_counts'][0]<0 for w in a['window_ratios']));self.assertTrue(all(c['status']=='INCOMPUTABLE' for c in a['curves'] if c['epoch']==4));self.assertFalse(any(p['replicated'] for p in a['comparisons']))
 def test_real_matrix_nonmonotone_and_censoring(self):
  m=self.module()
  for kind in ('left','left-nonmonotone','right','none'):
   r=self.data()
   for c in r['rows']:
    if c['shape']=='sparse' and c['offset']=='rotated':
     p=kind=='left' or (kind=='left-nonmonotone' and c['n']!=96) or (kind=='right' and c['n']==2048)
     for s in c['samples']:s['counts'][2]=c['loads']*int(p)
   a=m.analyze(r);c=next(c for c in a['curves'] if c['shape']=='sparse' and c['offset']=='rotated');self.assertEqual(c['status'],dict(left='left-censored',**{'left-nonmonotone':'ambiguous','right':'right-censored','none':'no-crossing-through2048'})[kind])
if __name__=='__main__':unittest.main()
