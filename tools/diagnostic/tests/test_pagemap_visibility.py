"""Actual C++ selector and decoder, external pagemap bits only simulated."""
import copy,importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class Visibility(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.folder=tempfile.TemporaryDirectory();d=Path(cls.folder.name);exe=d/'plan';subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(ROOT/'probes/diagnostic/pagemap_visibility.cpp'),'-o',str(exe)],check=True);cls.actual=[json.loads(l) for l in subprocess.check_output([str(exe),'--plan'],text=True).splitlines()]
 @classmethod
 def tearDownClass(cls):cls.folder.cleanup()
 def module(self):return importlib.import_module('tools.diagnostic.pagemap_visibility_analysis')
 def records(self):
  rr=copy.deepcopy(self.actual);rr.append(dict(type='runtime',cpu=7,base=4294967296));rr.append(dict(type='backing',stage='before',base_page_bytes=4096,anon_huge_kb=0))
  for stage in ('before','after'):
   for p in rr[1]['page_ids']:rr.append(dict(type='pagemap',stage=stage,page_id=p,entry=(1<<63)|(1<<56)|((p+12345)&((1<<55)-1))))
  rr.append(dict(type='backing',stage='after',base_page_bytes=4096,anon_huge_kb=0));return rr
 def test_real_plan_matches_selector(self):
  m=self.module();m.validate_plan(self.actual);self.assertEqual(len(self.actual[1]['page_ids']),47)
 def test_raw_bit_decoder_all_flags(self):
  d=Path(self.folder.name);s=d/'decode.cpp';exe=d/'decode';s.write_text(r"""#include "pagemap_decode.h"
#include <cstdio>
int main(){for(uint64_t v:{uint64_t(0),uint64_t(1)<<63,(uint64_t(1)<<62)|123,(uint64_t(1)<<63)|(uint64_t(1)<<56)|17,(uint64_t(1)<<63)|((uint64_t(1)<<55)-1)}){auto d=pagemap_decode(v);std::printf("%d %d %llu\n",d.present,d.swapped,static_cast<unsigned long long>(d.pfn));}}""");subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-include','initializer_list','-I',str(ROOT/'probes/common'),str(s),'-o',str(exe)],check=True);self.assertEqual(subprocess.check_output([str(exe)],text=True),f'0 0 0\n1 0 0\n0 1 123\n1 0 17\n1 0 {(1<<55)-1}\n')
 def test_three_real_shape_outputs_are_visible(self):
  m=self.module();a=m.audit_process(self.records(),self.actual);self.assertEqual((a['status'],a['pages'],a['unique_pfns']),('visible-stable',47,47))
 def test_masked_zero_never_promotes(self):
  m=self.module();rr=self.records()
  for r in rr:
   if r['type']=='pagemap':r['entry']&=~((1<<55)-1)
  a=m.audit_process(rr,self.actual);self.assertEqual(a['status'],'opaque-or-zero');self.assertEqual(a['nonzero'],0)
 def test_endpoint_change_and_swap_are_named(self):
  for kind in ('change','swap','partial','duplicate-pfn'):
   rr=self.records();entries=[r for r in rr if r['type']=='pagemap'];row=entries[47]
   if kind=='change':row['entry']+=1
   elif kind=='swap':row['entry']^=(1<<63)|(1<<62)
   elif kind=='partial':row['entry']&=~((1<<55)-1)
   else:entries[1]['entry']=entries[0]['entry']
   self.assertNotEqual(self.module().audit_process(rr,self.actual)['status'],'visible-stable',kind)
 def test_missing_order_types_and_backing_reject(self):
  for kind in ('missing','extra','order','base','entry','id','backing'):
   rr=self.records()
   if kind=='missing':rr.pop()
   elif kind=='extra':rr.append(rr[-1])
   elif kind=='order':rr[4:6]=rr[4:6][::-1]
   elif kind=='base':rr[2]['base']=True
   elif kind=='entry':rr[4]['entry']=True
   elif kind=='id':rr[4]['page_id']+=1
   else:rr[3]['anon_huge_kb']=1
   with self.subTest(kind=kind),self.assertRaises(ValueError):self.module().audit_process(rr,self.actual)
if __name__=='__main__':unittest.main()
