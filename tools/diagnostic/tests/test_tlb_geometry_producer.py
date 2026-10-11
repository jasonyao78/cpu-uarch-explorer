"""Real C++ collection/plan and paired-address geometry, not device evidence."""
import json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def expected_cells(reverse=False):
 cells=[]
 for t in (7,100,200):
  for s in (1,2,16):
   for d in (0,1):
    for h in (1,2):
     for w in (1,8,9):cells.append(dict(type='cell',cell=f't{t}-s{s}-h{h}-w{w}-d{d}',target=t,step=s,h=h,w=w,victim=0 if w==1 else 4,history_direction=0,direction=d,passes=8,rounds=16))
 if reverse:cells.reverse()
 return [dict(c,position=i) for i,c in enumerate(cells)]
class GeometryProducer(unittest.TestCase):
 def compile(self,path,source):
  self.assertTrue(Path(source).exists(),'geometry producer not delivered')
  exe=Path(path)/'producer';subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(source),'-o',str(exe)],check=True);return exe
 def test_real_plan_all_108_cells_15552_windows_and_bad_requests(self):
  with tempfile.TemporaryDirectory() as d:
   exe=self.compile(d,ROOT/'probes/diagnostic/tlb_address_geometry.cpp')
   for reverse in (False,True):
    rows=[json.loads(l) for l in subprocess.check_output([str(exe),'--plan',*(['--reverse'] if reverse else [])],text=True).splitlines()]
    self.assertEqual(rows[1:],expected_cells(reverse));self.assertEqual((rows[0]['cells'],rows[0]['windows']),(108,15552));self.assertIs(rows[0]['reverse'],reverse)
   for args in ([],['100'],['--plan','bad'],['--plan','--reverse','bad']):self.assertNotEqual(subprocess.run([str(exe),*args],capture_output=True).returncode,0)
 def test_real_selector_many_base_phases_and_actual_link_membership(self):
  self.assertTrue((ROOT/'probes/diagnostic/tlb_address_geometry_layout.h').exists(),'geometry selector missing')
  with tempfile.TemporaryDirectory() as d:
   src=Path(d)/'selector.cpp';src.write_text(r'''#include "tlb_address_geometry_layout.h"
#include <cstdio>
int main(){for(uintptr_t base:{0x100000000ull,0x100001000ull,0x10fffe000ull,0x110003000ull})for(unsigned t:{7u,100u,200u})for(unsigned s:{1u,2u,16u}){auto ts=tlb_geometry::targets(reinterpret_cast<char*>(base),65536,t,s);for(unsigned h=1;h<=2;++h){std::printf("%llu %u %u %u",static_cast<unsigned long long>(base),t,s,h);for(auto v:ts[h-1])std::printf(" %llu",static_cast<unsigned long long>(v));std::puts("");}}for(unsigned t:{0u,256u}){try{tlb_geometry::targets(reinterpret_cast<char*>(0x100000000ull),65536,t,3);return 2;}catch(const std::runtime_error&){}}}
''')
   exe=self.compile(d,src);lines=subprocess.check_output([str(exe)],text=True).splitlines();self.assertEqual(len(lines),72)
   for line in lines:
    base,t,s,h,*va=map(int,line.split());q0=((base>>12)+255)//256;want=[(((q0+i*s)<<8)|(t if h==1 else t^((q0+i*s)&255)))<<12 for i in range(12)];self.assertEqual(va,want);self.assertTrue(all(base<=v<base+65536*4096 for v in va))
if __name__=='__main__':unittest.main()
