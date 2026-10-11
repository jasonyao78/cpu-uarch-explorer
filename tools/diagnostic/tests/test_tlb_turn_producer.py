"""Real C++ collection/plan and paired-address geometry, not device evidence."""
import json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def expected_cells(reverse=False):
 cells=[]
 for t in (7,100):
  for s in (1,16):
   for d in (0,1):
    for h in (1,2):
     for w in (1,6,7,8,9,10):cells.append(dict(type='cell',cell=f't{t}-s{s}-h{h}-w{w}-d{d}',target=t,step=s,h=h,w=w,victim=0 if w==1 else 4,history_direction=0,direction=d,passes=8,rounds=16))
 if reverse:cells.reverse()
 return [dict(c,position=i) for i,c in enumerate(cells)]
class TurnProducer(unittest.TestCase):
 def compile(self,path,source):
  self.assertTrue(Path(source).exists(),'geometry producer not delivered')
  exe=Path(path)/'producer';subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(source),'-o',str(exe)],check=True);return exe
 def test_real_plan_all_96_cells_13824_windows_and_bad_requests(self):
  with tempfile.TemporaryDirectory() as d:
   exe=self.compile(d,ROOT/'probes/diagnostic/tlb_local_turn.cpp')
   for reverse in (False,True):
    rows=[json.loads(l) for l in subprocess.check_output([str(exe),'--plan',*(['--reverse'] if reverse else [])],text=True).splitlines()]
    self.assertEqual(rows[1:],expected_cells(reverse));self.assertEqual((rows[0]['cells'],rows[0]['windows']),(96,13824));self.assertIs(rows[0]['reverse'],reverse)
   for args in ([],['100'],['--plan','bad'],['--plan','--reverse','bad']):self.assertNotEqual(subprocess.run([str(exe),*args],capture_output=True).returncode,0)
 def test_real_selector_many_base_phases(self):
  self.assertTrue((ROOT/'probes/diagnostic/tlb_local_turn_layout.h').exists(),'geometry selector missing')
  with tempfile.TemporaryDirectory() as d:
   src=Path(d)/'selector.cpp';src.write_text(r'''#include "tlb_local_turn_layout.h"
#include <cstdio>
int main(){for(uintptr_t base:{0x100000000ull,0x100001000ull,0x10fffe000ull,0x110003000ull})for(unsigned t:{7u,100u})for(unsigned s:{1u,16u}){auto ts=tlb_turn::targets(reinterpret_cast<char*>(base),65536,t,s);for(unsigned h=1;h<=2;++h){std::printf("%llu %u %u %u",static_cast<unsigned long long>(base),t,s,h);for(auto v:ts[h-1])std::printf(" %llu",static_cast<unsigned long long>(v));std::puts("");}}for(unsigned t:{0u,256u}){try{tlb_turn::targets(reinterpret_cast<char*>(0x100000000ull),65536,t,3);return 2;}catch(const std::runtime_error&){}}}
''')
   exe=self.compile(d,src);lines=subprocess.check_output([str(exe)],text=True).splitlines();self.assertEqual(len(lines),32)
   for line in lines:
    base,t,s,h,*va=map(int,line.split());q0=((base>>12)+255)//256;want=[(((q0+i*s)<<8)|(t if h==1 else t^((q0+i*s)&255)))<<12 for i in range(12)];self.assertEqual(va,want);self.assertTrue(all(base<=v<base+65536*4096 for v in va))
 def test_actual_family_links_and_all_production_shots(self):
  with tempfile.TemporaryDirectory() as d:
   src=Path(d)/'trace.cpp';src.write_text(r'''#include "tlb_local_turn_layout.h"
#include <cstdio>
#include <sys/mman.h>
int main(){size_t bytes=65536ull*4096;char* memory=static_cast<char*>(mmap(nullptr,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0));if(memory==MAP_FAILED)return 2;auto families=tlb_turn::families(memory,65536);for(auto c:tlb_turn::cells(false)){const auto& pages=families[tlb_turn::family(c.target,c.step,c.h)];tlb_turn::link(pages,c);auto index=[&](uintptr_t p){for(unsigned i=0;i<12;++i)if(p==tlb_history::node(pages,i))return i;throw std::runtime_error("outside-family");};auto start=tlb_turn::history_start(pages,c),p=start;std::printf("H %s",c.id().c_str());for(unsigned i=0;i<12;++i){std::printf(" %u",index(p));p=tlb_history::walk(p,1,3);}if(p!=start)return 3;std::puts("");start=tlb_turn::competitor_start(pages,c);p=start;std::printf("C %s",c.id().c_str());for(unsigned i=0;i<c.w-1;++i){std::printf(" %u",index(p));p=tlb_history::walk(p,1,4);}if(p!=start)return 4;std::puts("");auto victim=tlb_history::node(pages,c.victim);if(tlb_history::walk(victim,1,0)!=victim)return 5;for(auto shot:tlb_turn::schedule(c))std::printf("S %s %u %u %u\n",c.id().c_str(),shot.round,shot.pass_index,shot.victim?1:0);}munmap(memory,bytes);}
''')
   exe=self.compile(d,src);actual=subprocess.check_output([str(exe)],text=True).splitlines();want=[]
   for c in expected_cells():
    order=[i for i in range(c['w']) if i!=c['victim']]
    if c['direction']:order.reverse()
    want.extend(['H '+c['cell']+' '+ ' '.join(map(str,range(12))),('C '+c['cell']+' '+ ' '.join(map(str,order))).rstrip()])
    want.extend(f"S {c['cell']} {r} {j} {int(j==8)}" for r in range(16) for j in range(9))
   self.assertEqual(actual,want);self.assertEqual(sum(l.startswith('S ') for l in actual),13824)
if __name__=='__main__':unittest.main()
