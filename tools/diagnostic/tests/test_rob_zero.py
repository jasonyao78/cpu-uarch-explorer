"""Actual C exporter and same-family zero/nonzero opcode counterexample."""
import hashlib,json,struct,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SOURCE='docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c'
class ZeroProducer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.folder=tempfile.TemporaryDirectory();d=Path(cls.folder.name);cls.exe=d/'producer'
  subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(ROOT/SOURCE),'-o',str(cls.exe)],check=True)
 @classmethod
 def tearDownClass(cls):cls.folder.cleanup()
 def export(self,c,a,n):
  f=Path(self.folder.name)/'body';p=subprocess.run([str(self.exe),'-t',c,'-a',a,'-n',str(n),'--chain','16','--align','0','--write-asm',str(f)],capture_output=True,text=True)
  self.assertEqual(p.returncode,0,'actual C exporter must accept mov0: '+p.stderr)
  return json.loads(p.stdout),f.read_bytes()
 def test_mov0_mov1_only_immediate_bit_diff_and_n0_identical(self):
  for a in ('none','fsqrt'):
   for n in (0,128,256,704):
    c0,b0=self.export('mov0',a,n);c1,b1=self.export('movi',a,n)
    self.assertEqual({k:v for k,v in c0.items() if k!='class'},{k:v for k,v in c1.items() if k!='class'})
    w0=struct.unpack('<'+'I'*(len(b0)//4),b0);w1=struct.unpack('<'+'I'*(len(b1)//4),b1);changed=[(x,y) for x,y in zip(w0,w1) if x!=y]
    self.assertEqual(len(changed),2*n)
    self.assertTrue(all(x^y==32 and x&0xffffffe0==0xd2800000 and 4<=x&31<=11 for x,y in changed))
    if n==0:self.assertEqual(b0,b1)
 def test_seven_legacy_class_exports_unchanged(self):
  d=Path(self.folder.name);legacy=d/'legacy'
  for p in (SOURCE,'probes/common/perf_group_read.h','probes/common/rob_backing.h'):(d/Path(p).name).write_bytes(subprocess.check_output(['git','show','1ef4baa:'+p],cwd=ROOT))
  subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(d),str(d/'rob_window_probe.c'),'-o',str(legacy)],check=True)
  for c in ('nop','add','movi','movr','fadd','ldr','str'):
   for a in ('none','fsqrt'):
    for n in (0,128):
     cfg,b=self.export(c,a,n);f=d/'oldbody';old=json.loads(subprocess.check_output([str(legacy),'-t',c,'-a',a,'-n',str(n),'--chain','16','--align','0','--write-asm',str(f)],text=True));self.assertEqual(cfg,old);self.assertEqual(b,f.read_bytes())
if __name__=='__main__':unittest.main()
