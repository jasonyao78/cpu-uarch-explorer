"""Actual C++ planner/selector and mapped pointer rings; no fabricated plans."""
import json,itertools,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'probes/diagnostic/tlb_cross_region.cpp'
def signatures(va):
 vpn=va>>12;lo=vpn&255;mid=(vpn>>8)&255;hi=(vpn>>16)&255
 return (lo,lo^mid,lo^hi,lo^mid^hi)
def expected_pages(base,t,g):
 a=(base+(1<<30)-1)//(1<<30)*(1<<30);q0=a>>20;hi0=(a>>28)&255
 return [((q0+(256*(i%4)+16*(i//4) if g else 16*i))<<20)|((t^(((q0+256*(i%4)+16*(i//4))>>8)&255)^hi0 if g==2 else t)<<12) for i in range(12)]
class RegionProducer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.exe=Path(cls.temp.name)/'producer'
  if SOURCE.exists():subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I'+str(ROOT/'probes/common'),'-I'+str(ROOT/'probes/diagnostic'),str(SOURCE),'-o',str(cls.exe)],check=True)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_real_plans_and_reverse_cells(self):
  self.assertTrue(SOURCE.exists(),'cross-region producer missing')
  for rev in (False,True):
   rr=[json.loads(l) for l in subprocess.check_output([str(self.exe),'--plan',*(['--reverse'] if rev else [])],text=True).splitlines()];self.assertEqual(len(rr),49);cfg,*cells=rr;self.assertEqual((cfg['probe'],cfg['cells'],cfg['windows']),('tlb-cross-region',48,6912));want=list(itertools.product((7,100),range(3),(0,1),(1,8,9,12)))
   if rev:want.reverse()
   self.assertEqual([(c['target'],c['group'],c['direction'],c['w']) for c in cells],want);self.assertEqual([c['position'] for c in cells],list(range(48)));self.assertTrue(all(c['victim']==0 and c['passes']==8 and c['rounds']==16 for c in cells))
 def test_real_geometry_models_victim_regions_and_descriptor_proxy(self):
  for base in (0x30001000,0x3f70001000,0x3fc0000000,0x3ff0001000):
   g=json.loads(subprocess.check_output([str(self.exe),'--layout',hex(base)],text=True));self.assertEqual(g['pool_base'],base);used=[set() for _ in range(4)]
   for f,(t,group) in zip(g['families'],itertools.product((7,100),range(3))):
    self.assertEqual((f['target'],f['group']),(t,group));pages=expected_pages(base,t,group);self.assertEqual(f['pages'],pages);counts=[len({signatures(v)[h] for v in pages}) for h in range(4)];self.assertEqual(counts,([1,12,1,12],[1,3,4,12],[4,12,1,3])[group]);regions=[(v-g['aligned_start'])//(1<<28) for v in pages];self.assertEqual([regions.count(i) for i in range(4)],[12,0,0,0] if group==0 else [3,3,3,3])
    for v in pages:
     for h,x in enumerate(signatures(v)):used[h].add(x)
   for offset in (0,3):
    a,b,c=g['families'][offset:offset+3];self.assertEqual(a['pages'][0],b['pages'][0]);self.assertEqual(b['pages'][0],c['pages'][0]);self.assertTrue(all((x>>21,(x>>12)&~7)==(y>>21,(y>>12)&~7) for x,y in zip(b['pages'],c['pages'])))
   f=g['filler_pages'];self.assertEqual(len(f),512);self.assertEqual(len(set(f)),512);self.assertTrue(all(x not in used[h] for v in f for h,x in enumerate(signatures(v))))
   expected=[]
   for i in range(2048):
    v=g['filler_base']+4096*i
    if all(x not in used[h] for h,x in enumerate(signatures(v))):expected.append(v)
    if len(expected)==512:break
   self.assertEqual(sorted(f),expected)
  for arg in ('0','-1','abc','0xffffffffffffffff','0x30000001'):
   self.assertNotEqual(subprocess.run([str(self.exe),'--layout',arg],capture_output=True).returncode,0)
 def test_actual_mapped_links_all_cells_and_closed_filler(self):
  source=r"""
#include "tlb_cross_region_layout.h"
#include "page_policy.h"
#include <iostream>
int main(){auto m=probe_common::map_guarded_anonymous(524288ull*4096,static_cast<size_t>(sysconf(_SC_PAGESIZE)));auto f=probe_common::map_guarded_anonymous(2048ull*4096,static_cast<size_t>(sysconf(_SC_PAGESIZE)));if(!m.buf||!f.buf)return 1;auto ts=tlb_region::families(m.buf,524288);auto ff=tlb_region::fillers(f.buf,2048,ts);tlb_history::link_filler(ff);if(tlb_history::walk(ff[0],128,1)!=ff[0])return 2;for(auto c:tlb_region::cells(false)){auto& pp=ts[tlb_region::family(c.target,c.group)];tlb_region::link(pp,c);if(tlb_history::walk(pp[0],1,0)!=pp[0]||tlb_history::walk(pp[0],12,3)!=pp[0])return 3;auto want=tlb_region::competitor_indices(c);uintptr_t v=tlb_region::competitor_start(pp,c);for(auto i:want){if(v!=tlb_history::node(pp,i))return 4;v=tlb_history::walk(v,1,4);}if(!want.empty()&&v!=tlb_region::competitor_start(pp,c))return 5;auto ss=tlb_region::schedule(c);if(ss.size()!=144||ss.back().round!=15||!ss.back().victim)return 6;}munmap(m.mapping_base,m.mapping_bytes);munmap(f.mapping_base,f.mapping_bytes);std::cout<<"48 real cells, closed rings\n";}
"""
  with tempfile.TemporaryDirectory() as d:
   c=Path(d)/'harness.cpp';c.write_text(source);exe=Path(d)/'harness';subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I'+str(ROOT/'probes/common'),'-I'+str(ROOT/'probes/diagnostic'),str(c),'-o',str(exe)],check=True);self.assertIn('48 real cells',subprocess.check_output([str(exe)],text=True))
if __name__=='__main__':unittest.main()
