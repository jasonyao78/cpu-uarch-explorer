"""Real dose producer contracts; no physical target claims from native plans."""
import collections,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class DoseProducer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.src=ROOT/'probes/diagnostic/tlb_descriptor_dose.c';cls.tmp=tempfile.TemporaryDirectory();cls.binary=Path(cls.tmp.name)/'dose'
  if cls.src.exists():subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(cls.src),'-o',str(cls.binary)],check=True,capture_output=True)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def plan(self,n=1536,s=515,rev=0):
  self.assertTrue(self.src.exists(),'descriptor dose actual producer missing');return json.loads(subprocess.check_output([str(self.binary),'--plan','--nodes',str(n),'--reverse',str(rev),'--stride-pages',str(s)],text=True))
 def test_actual_all_dose_histogram_quartets_and_footprints(self):
  for s,pages in zip((5,67,131,169,173,259,515),(15,201,393,507,519,777,1536)):
   for rev in (0,1):
    p=self.plan(s=s,rev=rev);self.assertEqual(p['strides'],[20480,s*4096]);self.assertEqual(p['probe'],'tlb-descriptor-dose');self.assertEqual(p['kernel_words'],[0xf9400000,0x9b092800,0xf1000508,0x54ffffa1]);self.assertEqual(p['captures'],3072)
    for stride in p['strides']:
     va=[i*stride for i in range(1536)];self.assertEqual(collections.Counter((a>>12)&255 for a in va),collections.Counter({i:6 for i in range(256)}));self.assertEqual(len({a>>14 for a in va}),1536)
    self.assertEqual(len({(i*s)>>9 for i in range(1536)}),pages);j=p['order'][0];seen=[]
    for _ in range(1536):seen.append(j);j=p['next'][j]
    self.assertEqual(sorted(seen),list(range(1536)));self.assertEqual(j,p['order'][0]);self.assertEqual(p['loads']%1536,0)
 def test_qualification_small_geometry_and_duplicate_dose_negative(self):
  p=self.plan(32,515);self.assertEqual((p['captures'],p['windows']),(64,12));p=self.plan(s=5);self.assertEqual(p['strides'][0],p['strides'][1])
 def test_unregistered_args_and_host_sampling_refuse(self):
  self.plan()
  for args in (['--plan','--nodes','1792','--reverse','0','--stride-pages','515'],['--plan','--nodes','32','--reverse','0','--stride-pages','171'],['--run','--nodes','32','--reverse','0','--stride-pages','515']):
   q=subprocess.run([str(self.binary),*args],text=True,capture_output=True);self.assertNotEqual(q.returncode,0);self.assertEqual(json.loads(q.stdout)['metrics'],{})
