"""同VA/PFN关联布局的实际C++与host映射检查；PFN输入是软件合成，非真机证据。

契约：docs/design/2026-10-12-tlb-pfn-association.md。守住mod64、bijective、
零邻接和同物理图；不能用打乱页集合的近似实现替代这些控制条件。
"""
import random,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HEADER=ROOT/'probes/diagnostic/tlb_pfn_association_layout.h'
class AssociationLayout(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not HEADER.exists():raise AssertionError('association layout missing')
  cls.temp=tempfile.TemporaryDirectory();cls.folder=Path(cls.temp.name);s=cls.folder/'layout.cpp';cls.exe=s.with_suffix('')
  s.write_text(r'''#include "tlb_pfn_association_layout.h"
#include <iostream>
int main(int argc,char**argv){try{std::vector<uint64_t> p;uint64_t x;unsigned n;if(!(std::cin>>n))return 2;for(unsigned j=0;j<n;++j){if(!(std::cin>>x))return 3;p.push_back(x);}auto v=tlb_association::weave(p);if(argc>1){std::string b=argv[1];if(b=="duplicate")v[0]=v[64];else if(b=="residue")std::swap(v[0],v[1]);else if(b=="bounds")v[0]=n;else if(b=="identity"){for(unsigned j=0;j<n;++j)v[j]=j;}}tlb_association::validate(p,v,true);for(unsigned j=0;j<n;++j)std::cout<<(j?" ":"")<<v[j];std::cout<<"\n";return 0;}catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 1;}}''')
  subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(HEADER.parent),str(s),'-o',str(cls.exe)],check=True)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def execute(self,p,bad=None):
  return subprocess.run([str(self.exe),*([bad] if bad else [])],input=str(len(p))+'\n'+' '.join(map(str,p))+'\n',text=True,capture_output=True)
 def check(self,p):
  r=self.execute(p);self.assertEqual(r.returncode,0,r.stderr);v=list(map(int,r.stdout.split()));self.assertEqual(sorted(v),list(range(len(p))));self.assertTrue(all(i%64==j%64 for i,j in enumerate(v)));self.assertTrue(all(abs(p[v[j+1]]-p[v[j]])!=1 for j in range(len(p)-1)));self.assertEqual(r.stdout,self.execute(p).stdout)
 def test_actual_all_grids_and_adversarial_physical_orders(self):
  for n in (1024,1280,1536,1792,2048,2304,2560,3072):
   for kind in ('ascending','descending','shuffled','gapped','upper-edge'):
    p=list(range(1000,1000+n))
    if kind=='descending':p.reverse()
    elif kind=='shuffled':random.Random(271).shuffle(p)
    elif kind=='gapped':p=[1000+3*j for j in range(n)]
    elif kind=='upper-edge':p=list(range((1<<55)-n,(1<<55)))
    with self.subTest(n=n,kind=kind):self.check(p)
 def test_bad_pfn_or_dimension_reject(self):
  for p in ([1]*1024,[0,*range(2,1025)],[(1<<55),*range(2,1025)],list(range(1,1024)),list(range(1,1026)),list(range(1,4098))):
   with self.subTest(n=len(p)),self.assertRaises(AssertionError):self.check(p)
 def test_mutated_permutation_or_false_no_adjacency_certificate_reject(self):
  for b in ('duplicate','residue','bounds','identity'):
   with self.subTest(bad=b):self.assertEqual(self.execute(list(range(1000,2024)),b).returncode,1)
 def test_already_no_adjacent_input_is_not_fake_excitation(self):
  p=[1000+3*j for j in range(1024)];r=self.execute(p);self.assertEqual(r.returncode,0);self.assertEqual(list(map(int,r.stdout.split())),list(range(1024)))
 def test_actual_host_remap_keeps_virtual_lines_and_physical_closed_graph(self):
  s=self.folder/'mapping.cpp';exe=s.with_suffix('');s.write_text(r'''#include "tlb_pfn_association_layout.h"
#include <sys/mman.h>
#include <unistd.h>
#include <cstdio>
#include <set>
int main(){const unsigned n=1024;size_t page=size_t(sysconf(_SC_PAGESIZE)),bytes=n*page;char name[]="/tmp/assoc-XXXXXX";int fd=mkstemp(name);if(fd<0)return 1;unlink(name);if(ftruncate(fd,bytes))return 2;void* canonical=mmap(nullptr,bytes,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);void* arena=mmap(nullptr,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);if(canonical==MAP_FAILED||arena==MAP_FAILED)return 3;std::vector<uint64_t> pfns(n);for(unsigned i=0;i<n;++i)pfns[i]=1000+i;auto v=tlb_association::weave(pfns);std::set<uintptr_t> lines;
for(unsigned mode=0;mode<2;++mode){std::vector<unsigned> inv(n);std::set<uintptr_t> now;for(unsigned j=0;j<n;++j){unsigned i=mode?v[j]:j;inv[i]=j;char* a=static_cast<char*>(arena)+j*page;if(mmap(a,page,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_FIXED,fd,i*page)!=a)return 4;now.insert(reinterpret_cast<uintptr_t>(a)+64*(i%64));}if(mode&&now!=lines)return 5;lines=now;auto node=[&](unsigned i){return reinterpret_cast<uintptr_t>(arena)+inv[i]*page+64*(i%64);};for(unsigned i=0;i<n;++i)*reinterpret_cast<uintptr_t*>(static_cast<char*>(canonical)+i*page+64*(i%64))=node((i+1)%n)^UINT64_C(0x9e3779b97f4a7c15);uintptr_t h=node(0);for(unsigned i=0;i<n;++i){if(h!=node(i))return 6;uint64_t a=*reinterpret_cast<uint64_t*>(h),b=*reinterpret_cast<uint64_t*>(static_cast<char*>(canonical)+i*page+64*(i%64));if(a!=b)return 7;h=a^UINT64_C(0x9e3779b97f4a7c15);}if(h!=node(0))return 8;}munmap(arena,bytes);munmap(canonical,bytes);close(fd);puts("1024 physical nodes, identical VA lines, two closed graphs");}''')
  subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(HEADER.parent),str(s),'-o',str(exe)],check=True)
  self.assertEqual(subprocess.check_output([str(exe)],text=True),'1024 physical nodes, identical VA lines, two closed graphs\n')
if __name__=='__main__':unittest.main()
