"""Real producer and physical graph traversal; PMU/phone evidence separate."""
import json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def expected(reverse=False):
 rows=[dict(type='cell',cell='floor',scope='floor',layout='empty',k=0,nodes=0,loads=0,iterations=0,pages=0,line_bytes=0,span_bytes=0,rounds=3)]
 for scope in ('total','per-chain'):
  for layout in ('high','low'):
   for k in (1,2,4,8):
    n=8192*(k if scope=='per-chain' else 1);pages=n if layout=='high' else n//64;span=((n-1)*17+1)*4096 if layout=='high' else pages*4096
    for loads in (262144,1048576):rows.append(dict(type='cell',cell=f'{scope}-{layout}-k{k}-l{loads}',scope=scope,layout=layout,k=k,nodes=n,loads=loads,iterations=loads//k,pages=pages,line_bytes=n*64,span_bytes=span,rounds=3))
 if reverse:rows.reverse()
 return [dict(c,position=i) for i,c in enumerate(rows)]
def shuffled(n):
 order=list(range(n));state=137;mask=(1<<64)-1
 for i in range(n-1,0,-1):
  state^=(state<<13)&mask;state^=state>>7;state^=(state<<17)&mask;j=state%(i+1);order[i],order[j]=order[j],order[i]
 return order
class ParallelProducer(unittest.TestCase):
 def compile(self,d,src):
  self.assertTrue(src.exists(),'K-chain producer missing')
  exe=Path(d)/'producer';subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(src),'-o',str(exe)],check=True);return exe
 def test_actual_plan_and_request_guard(self):
  with tempfile.TemporaryDirectory() as d:
   exe=self.compile(d,ROOT/'probes/diagnostic/tlb_walk_parallel.cpp')
   for rev in (False,True):
    rows=[json.loads(x) for x in subprocess.check_output([str(exe),'--plan',*(['--reverse'] if rev else [])],text=True).splitlines()];self.assertEqual(rows[1:],expected(rev));self.assertEqual((rows[0]['cells'],rows[0]['windows']),(33,99))
   for args in ([],['--run','8'],['--plan','--bad'],['--plan','--reverse','extra']):self.assertNotEqual(subprocess.run([str(exe),*args],capture_output=True).returncode,0)
 def test_actual_chain_traversal_footprint_and_full_permutation(self):
  self.assertTrue((ROOT/'probes/diagnostic/tlb_walk_parallel_layout.h').exists(),'K-chain layout missing')
  with tempfile.TemporaryDirectory() as d:
   src=Path(d)/'trace.cpp';src.write_text(r'''#include "tlb_walk_parallel_layout.h"
#include <cstdio>
#include <sys/mman.h>
int main(){for(auto c:tlb_parallel::cells(false)){if(!c.k || c.loads!=262144)continue;auto* mem=static_cast<char*>(mmap(nullptr,c.span_bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0));if(mem==MAP_FAILED)return 2;auto chains=tlb_parallel::indices(c);auto heads=tlb_parallel::link(mem,c,chains);for(unsigned k=0;k<c.k;++k){uintptr_t p=heads[k];std::printf("%s %u",c.id().c_str(),k);for(auto i:chains[k]){if(p!=reinterpret_cast<uintptr_t>(mem)+tlb_parallel::offset(c,i))return 3;std::printf(" %u",i);p=*reinterpret_cast<uintptr_t*>(p);}if(p!=heads[k])return 4;std::puts("");}munmap(mem,c.span_bytes);}}
''');exe=self.compile(d,src);rows=subprocess.check_output([str(exe)],text=True).splitlines();cursor=0
   for c in expected():
    if not c['k'] or c['loads']!=262144:continue
    order=shuffled(c['nodes']);size=c['nodes']//c['k']
    for k in range(c['k']):
     name,kk,*nodes=rows[cursor].split();cursor+=1;self.assertEqual((name,int(kk),list(map(int,nodes))),(c['cell'],k,order[k*size:(k+1)*size]))
   self.assertEqual(cursor,len(rows))
if __name__=='__main__':unittest.main()
