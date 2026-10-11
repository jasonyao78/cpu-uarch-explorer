"""Real production plan and C selector to controlled external PMU observations."""
import copy,importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class TurnAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.folder=tempfile.TemporaryDirectory();d=Path(cls.folder.name);exe=d/'plan'
  subprocess.run(['clang++','-std=c++17','-O2','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(ROOT/'probes/diagnostic/tlb_local_turn.cpp'),'-o',str(exe)],check=True)
  cls.actual={key:[json.loads(l) for l in subprocess.check_output([str(exe),'--plan',*opts],text=True).splitlines()] for key,opts in [('forward',[]),('reverse',['--reverse'])]}
  src=d/'selector.cpp';src.write_text(r'''#include "tlb_local_turn_layout.h"
#include <cstdio>
void arr(const tlb_local::Addresses& a){std::printf("[");for(size_t i=0;i<a.size();++i)std::printf("%s%llu",i?",":"",(unsigned long long)a[i]);std::printf("]");}
int main(){auto ts=tlb_turn::families((char*)0x40000000ull,65536);std::printf("{\"type\":\"geometry\",\"pool_base\":1073741824,\"pool_pages\":65536,\"families\":[");bool first=true;for(unsigned t:{7u,100u})for(unsigned s:{1u,16u})for(unsigned h:{1u,2u}){std::printf("%s{\"target\":%u,\"step\":%u,\"h\":%u,\"pages\":",first?"":",",t,s,h);first=false;arr(ts[tlb_turn::family(t,s,h)]);std::printf("}");}std::printf("],\"filler_pages\":");arr(tlb_local::fillers((char*)0x80000000ull,2048,ts));std::puts("}");}
''')
  exe=d/'selector';subprocess.run(['clang++','-std=c++17','-O2','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(src),'-o',str(exe)],check=True);cls.geometry=json.loads(subprocess.check_output([str(exe)],text=True))
 @classmethod
 def tearDownClass(cls):cls.folder.cleanup()
 def module(self):
  self.assertTrue((ROOT/'tools/diagnostic/tlb_turn_analysis.py').exists(),'geometry consumer missing');return importlib.import_module('tools.diagnostic.tlb_turn_analysis')
 def records(self,reverse=False):
  rows=copy.deepcopy([self.actual['reverse' if reverse else 'forward'][0],self.geometry])
  for c in self.actual['reverse' if reverse else 'forward'][1:]:
   rows.extend(dict(type='backing',cell=c['cell'],stage=s,base_page_bytes=4096,anon_huge_kb=0) for s in ('before','after'))
   for t in range(16):
    for p in range(9):
     v=p==8;k=1 if v else c['w']-1;walk=int(v and c['h']==1 and c['w']>=(8 if c['target']==7 else 9))
     rows.append(dict(type='round',**{k:v for k,v in c.items() if k not in ('type','rounds')},round=t,role='victim' if v else 'competition',pass_index=p,enabled=100,running=100,counts=[200,k,walk,k,walk,0]))
  return rows
 def test_actual_plan_geometry_and_all_samples(self):
  m=self.module();m.validate_plan(self.actual)
  for reverse in (False,True):self.assertEqual(len(m.audit_process(self.records(reverse),reverse,self.actual)),96)
 def test_coverage_geometry_type_mux_and_requested_dimensions_reject(self):
  m=self.module();r=self.records()
  for kind in ('missing','duplicate','order','typed-target','step','role','mux','count','VA','filler','backing','plan'):
   rr=copy.deepcopy(r);p=copy.deepcopy(self.actual)
   if kind=='missing':rr.pop()
   elif kind=='duplicate':rr.append(rr[-1])
   elif kind=='order':rr[-2:]=rr[-2:][::-1]
   elif kind=='typed-target':rr[4]['target']=True
   elif kind=='step':rr[4]['step']=3
   elif kind=='role':rr[4]['role']='victim'
   elif kind=='mux':rr[4]['running']=1
   elif kind=='count':rr[4]['counts'][1]=True
   elif kind=='VA':rr[1]['families'][0]['pages'][0]+=4096
   elif kind=='filler':rr[1]['filler_pages'][0]=rr[1]['families'][0]['pages'][0]
   elif kind=='backing':rr[2]['anon_huge_kb']=1
   elif kind=='plan':p['forward'][1]['step']=3
   with self.subTest(kind=kind),self.assertRaises(ValueError):m.audit_process(rr,False,p)
 def run_data(self):
  m=self.module();return dict(mode=m.MODE,processes=5,rows=[dict(r,epoch=f'epoch-{e}') for e in range(5) for r in m.audit_process(self.records(bool(e%2)),bool(e%2),self.actual)])
 def test_complete_geometry_replication_and_negative_evidence_not_cherry_picked(self):
  m=self.module();run=self.run_data();a=m.analyze(run);self.assertTrue(a['all_lookup_observable']);self.assertEqual(sum(p['passed'] for p in a['replication']),10);self.assertEqual(len(a['replication']),40);self.assertFalse(a['physical_ways_certified'])
  for kind in ('lookup','residual','control-background','one-epoch-missing-response'):
   r=copy.deepcopy(run)
   for cell in r['rows']:
    if cell['target']==100 and cell['step']==16 and cell['h']==1:
     for shot in cell['samples']:
      if kind=='lookup' and cell['w']==9 and shot['role']=='competition':shot['counts'][1]=0
      if kind=='residual' and cell['w']==9 and shot['role']=='victim':shot['counts'][4]=2
      if kind=='control-background' and cell['w']==1 and shot['role']=='victim':shot['counts'][4]=1
      if kind=='one-epoch-missing-response' and cell['epoch']=='epoch-4' and cell['w']==9 and shot['role']=='victim':shot['counts'][4]=0
   a=m.analyze(r);p=next(p for p in a['replication'] if p['target']==100 and p['step']==16 and p['h']==1 and p['w']==9);self.assertFalse(p['passed'],kind)
  for bad in (dict(run,rows=run['rows'][:-1]),dict(run,rows=run['rows'][::-1])):
   with self.assertRaises(ValueError):m.analyze(bad)
 def test_production_curves_censor_nonmonotone_and_exposure_are_named(self):
  m=self.module();data=self.run_data();a=m.analyze(data)
  onset=next(p for p in a['onsets'] if p['target']==7 and p['step']==1 and p['h']==1)
  self.assertEqual((onset['status'],onset['interval']),('replicated-operational-interval',[7,8]))
  for kind in ('left','left-nonmonotone','right','nonmonotone','lookup'):
   r=copy.deepcopy(data)
   for cell in r['rows']:
    if cell['target']==7 and cell['step']==1 and cell['h']==1 and cell['w']!=1:
     for shot in cell['samples']:
      if shot['role']=='victim':
       if kind=='left':shot['counts'][4]=1
       elif kind=='left-nonmonotone':shot['counts'][4]=int(cell['w']!=7)
       elif kind=='right':shot['counts'][4]=int(cell['w']==10)
       elif kind=='nonmonotone' and cell['w']==9:shot['counts'][4]=0
      elif kind=='lookup':shot['counts'][1]=0
   a=m.analyze(r);p=next(p for p in a['onsets'] if p['target']==7 and p['step']==1 and p['h']==1)
   self.assertEqual(p['status'],{'left':'left-censored','left-nonmonotone':'ambiguous','right':'right-censored','nonmonotone':'ambiguous','lookup':'INCOMPUTABLE'}[kind])
if __name__=='__main__':unittest.main()
