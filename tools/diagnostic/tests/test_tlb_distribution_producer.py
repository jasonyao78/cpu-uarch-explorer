"""Real Q-A production plan, sets, offsets and graph traversal."""
import json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
GRID=(32,64,80,96,112,128,160,192,256,512,1024,2048)
def shuffle(n,seed):
 out=list(range(n));x=seed;mask=(1<<64)-1
 for i in range(n-1,0,-1):
  x^=(x<<13)&mask;x^=x>>7;x^=(x<<17)&mask;j=x%(i+1);out[i],out[j]=out[j],out[i]
 return out
GROUPS=shuffle(4096,271)
def pages(shape,n):return list(range(n)) if shape=='contiguous' else [65*i for i in range(n)] if shape=='sparse' else [64*GROUPS[i]+i%64 for i in range(n)]
def expected(reverse=False):
 rows=[dict(type='cell',cell='floor',shape='floor',offset='empty',order='empty',n=0,loads=0,span_bytes=0,line_bytes=0,rounds=3)]
 for shape in ('contiguous','sparse','random-set'):
  for off in ('constant','rotated'):
   for order in ('random','reverse-random'):
    for n in GRID:
     pp=pages(shape,n);rows.append(dict(type='cell',cell=f'{shape}-{off}-{order}-n{n}',shape=shape,offset=off,order=order,n=n,loads=(1048576//n)*n,span_bytes=(max(pp)-min(pp)+1)*4096,line_bytes=n*64,rounds=3))
 if reverse:rows.reverse()
 return [dict(c,position=i) for i,c in enumerate(rows)]
class DistributionProducer(unittest.TestCase):
 def compile(self,d,src):
  self.assertTrue(src.exists(),'page distribution producer missing');exe=Path(d)/'producer';subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(src),'-o',str(exe)],check=True);return exe
 def test_real_frozen_plan_and_bad_arguments(self):
  with tempfile.TemporaryDirectory() as d:
   exe=self.compile(d,ROOT/'probes/diagnostic/tlb_page_distribution.cpp')
   for reverse in (False,True):
    rows=[json.loads(l) for l in subprocess.check_output([str(exe),'--plan',*(['--reverse'] if reverse else [])],text=True).splitlines()];self.assertEqual(rows[1:],expected(reverse));self.assertEqual((rows[0]['cells'],rows[0]['windows']),(145,435))
   for args in ([],['--run','32'],['--plan','--bad'],['--plan','--reverse','extra']):self.assertNotEqual(subprocess.run([str(exe),*args],capture_output=True).returncode,0)
 def test_real_mapped_chains_exact_sets_offsets_histogram_and_return(self):
  self.assertTrue((ROOT/'probes/diagnostic/tlb_page_distribution_layout.h').exists(),'page distribution graph missing')
  with tempfile.TemporaryDirectory() as d:
   src=Path(d)/'graph.cpp';src.write_text(r'''#include "tlb_page_distribution_layout.h"
#include <cstdio>
#include <sys/mman.h>
int main(){size_t bytes=262144ull*4096;auto* mem=static_cast<char*>(mmap(nullptr,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0));if(mem==MAP_FAILED)return 2;for(auto c:tlb_distribution::cells(false)){if(!c.n)continue;auto pages=tlb_distribution::pages(c.shape,c.n);auto order=tlb_distribution::order(c);auto head=tlb_distribution::link(mem,c,pages,order),p=head;std::printf("%s",c.id().c_str());for(auto i:order){if(p!=reinterpret_cast<uintptr_t>(mem)+pages[i]*4096ull+tlb_distribution::offset(c,pages[i]))return 3;std::printf(" %u:%u",pages[i],tlb_distribution::offset(c,pages[i]));p=*reinterpret_cast<uintptr_t*>(p);}if(p!=head)return 4;std::puts("");}munmap(mem,bytes);}
''');exe=self.compile(d,src);rows=subprocess.check_output([str(exe)],text=True).splitlines();expected_rows=[]
   for c in expected()[1:]:
    pp=pages(c['shape'],c['n']);oo=shuffle(c['n'],137)
    if c['order']=='reverse-random':oo.reverse()
    expected_rows.append(c['cell']+' '+ ' '.join(f"{pp[i]}:{0 if c['offset']=='constant' else 64*(pp[i]%64)}" for i in oo))
   self.assertEqual(rows,expected_rows)
if __name__=='__main__':unittest.main()
