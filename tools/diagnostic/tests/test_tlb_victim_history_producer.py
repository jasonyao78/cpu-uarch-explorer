"""Actual C++ planner and pointer traces; no synthetic device claims."""
import json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def cells(reverse=False):
 out=[]
 for hd in (0,1):
  for w in (1,8,9):
   for v in ([0] if w==1 else [0,w//2,w-1]):
    for d in (0,1):
     for h in (1,2):out.append(dict(h=h,w=w,victim=v,history_direction=hd,direction=d,passes=8,rounds=16))
 if reverse:out.reverse()
 return [dict(type='cell',cell=f"victim-h{c['h']}-w{c['w']}-v{c['victim']}-hist{c['history_direction']}-d{c['direction']}",position=i,**c) for i,c in enumerate(out)]
class VictimProducer(unittest.TestCase):
 def compile(self,folder,source):
  exe=Path(folder)/'producer'
  try:subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(source),'-o',str(exe)],check=True,capture_output=True)
  except subprocess.CalledProcessError as e:self.fail('actual victim producer unavailable: '+e.stderr.decode()[:600])
  return exe
 def test_real_plan_budget_and_bad_argv(self):
  with tempfile.TemporaryDirectory() as d:
   exe=self.compile(d,ROOT/'probes/diagnostic/tlb_victim_history.cpp')
   for reverse in (False,True):
    rr=[json.loads(l) for l in subprocess.check_output([str(exe),'--plan',*(['--reverse'] if reverse else [])],text=True).splitlines()]
    self.assertEqual(rr[1:],cells(reverse));self.assertEqual((rr[0]['cells'],rr[0]['windows']),(56,8064));self.assertIs(rr[0]['reverse'],reverse);self.assertEqual(rr[0]['w_grid'],[1,8,9])
   for a in ([],['200'],['--plan','--bad'],['--plan','--reverse','bad']):self.assertNotEqual(subprocess.run([str(exe),*a],capture_output=True).returncode,0)
 def test_actual_links_trace_all_pages_and_8064_scheduled_windows(self):
  with tempfile.TemporaryDirectory() as d:
   src=Path(d)/'trace.cpp';src.write_text(r'''#include "tlb_victim_history_layout.h"
#include <cstdio>
#include <cstdlib>
int main(){auto memory=static_cast<char*>(std::calloc(12,4096));tlb_local::Addresses pages;for(unsigned i=0;i<12;++i)pages.push_back(reinterpret_cast<uintptr_t>(memory+4096*i));auto index=[&](uintptr_t p){for(unsigned i=0;i<12;++i)if(p==tlb_history::node(pages,i))return i;throw std::runtime_error("outside-pool");};for(auto c:tlb_victim_history::cells(false)){tlb_victim_history::link(pages,c);auto hist=tlb_victim_history::history_start(pages,c);auto p=hist;std::printf("H %s",c.id().c_str());for(unsigned i=0;i<12;++i){std::printf(" %u",index(p));p=tlb_history::walk(p,1,3);}if(p!=hist)return 4;std::puts("");auto start=tlb_victim_history::competitor_start(pages,c);p=start;std::printf("C %s",c.id().c_str());for(unsigned i=0;i<c.w-1;++i){std::printf(" %u",index(p));p=tlb_history::walk(p,1,4);}if(p!=start || tlb_history::walk(tlb_history::node(pages,c.victim),1,0)!=tlb_history::node(pages,c.victim))return 5;std::puts("");for(auto s:tlb_victim_history::schedule(c))std::printf("S %s %u %u %u\n",c.id().c_str(),s.round,s.pass_index,s.victim?1:0);}for(unsigned bad:{0u,2u,7u,10u}){auto c=tlb_victim_history::cells(false).front();c.w=bad;try{tlb_victim_history::link(pages,c);return 6;}catch(const std::runtime_error&){}}for(unsigned field=0;field<6;++field){auto c=tlb_victim_history::cells(false)[8];if(field==0)c.h=0;if(field==1)c.victim=3;if(field==2)c.history_direction=2;if(field==3)c.direction=2;if(field==4)c.passes=4;if(field==5)c.rounds=15;try{tlb_victim_history::link(pages,c);return 7;}catch(const std::runtime_error&){}}auto zero=tlb_victim_history::cells(false).front();if(tlb_victim_history::competitor_start({},zero)!=0)return 8;std::free(memory);}
''')
   exe=self.compile(d,src);actual=subprocess.check_output([str(exe)],text=True).splitlines();expected=[]
   for c in cells():
    history=list(range(12));competitors=[i for i in range(c['w']) if i!=c['victim']]
    if c['history_direction']:history.reverse()
    if c['direction']:competitors.reverse()
    expected.extend(['H '+c['cell']+' '+ ' '.join(map(str,history)),('C '+c['cell']+' '+ ' '.join(map(str,competitors))).rstrip()])
    expected.extend(f"S {c['cell']} {r} {p} {int(p==8)}" for r in range(16) for p in range(9))
   self.assertEqual(actual,expected);self.assertEqual(sum(l.startswith('S ') for l in actual),8064)
if __name__=='__main__':unittest.main()
