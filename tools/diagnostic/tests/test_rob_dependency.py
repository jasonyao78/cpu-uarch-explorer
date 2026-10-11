"""Actual C export: same output values and sole ADD source-field difference."""
import json,struct,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SOURCE='docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c'
class DependencyProducer(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.d=tempfile.TemporaryDirectory();cls.exe=Path(cls.d.name)/'producer'
  subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(ROOT/SOURCE),'-o',str(cls.exe)],check=True)
 @classmethod
 def tearDownClass(cls):cls.d.cleanup()
 def export(self,opts):
  f=Path(self.d.name)/'code';cfg=json.loads(subprocess.check_output([str(self.exe),*opts,'--write-asm',str(f)],text=True));return cfg,f.read_bytes()
 def test_pair_result_value_and_unique_source_field_all_conditions(self):
  for anchor,k in (('none',16),('fsqrt',8),('fsqrt',16)):
   for n in (0,64,128,256):
    base=['-t','add','-a',anchor,'--chain',str(k),'-n',str(n)];ci,bi=self.export(base+['--anchor-link','independent']);cd,bd=self.export(base+['--anchor-link','dependent'])
    self.assertEqual((ci['anchor_link'],cd['anchor_link']),('independent','dependent'));self.assertEqual(ci['bridges_per_iteration'],2)
    for c in (ci,cd):self.assertEqual(c['loop_instructions'],2*n+(2*k if anchor=='fsqrt' else 0)+4)
    wi=list(struct.unpack('<'+'I'*(len(bi)//4),bi));wd=list(struct.unpack('<'+'I'*(len(bd)//4),bd));changed=[(a,b) for a,b in zip(wi,wd) if a!=b];self.assertEqual(len(wi),len(wd));self.assertEqual(len(changed),2*n)
    for a,b in changed:self.assertEqual(a^b,28<<5);self.assertEqual((a>>5)&31,16);self.assertEqual((b>>5)&31,12);self.assertTrue(4<=a&31<=11);self.assertEqual((a>>16)&31,17)
    loop=wi[ci['loop_offset']//4:ci['branch_offset']//4+1];self.assertEqual(loop.count(0x9e66000c),2)
    # Both input sources have sqrt(1.0) bits; same ADD result, not zero vs nonzero.
    self.assertEqual(struct.unpack('<Q',struct.pack('<d',1.0))[0],0x3ff0000000000000)
    prefix=wi[:ci['loop_offset']//4];value=0
    for w in prefix:
     if w&31!=16:continue
     if w&0xff800000==0xd2800000:value=((w>>5)&65535)<<(((w>>21)&3)*16)
     elif w&0xff800000==0xf2800000:
      sh=((w>>21)&3)*16;value=(value&~(65535<<sh))|(((w>>5)&65535)<<sh)
    self.assertEqual(value,0x3ff0000000000000)
 def test_reject_incompatible_request_shapes(self):
  for extra in (['-t','nop'],['-a','miss'],['--paired'],['--asymmetric'],['--pointer-xor','0'],['--anchor-link','bad']):
   r=subprocess.run([str(self.exe),'-t','add','-a','fsqrt','-n','64','--anchor-link','independent',*extra,'--write-asm',str(Path(self.d.name)/'bad')],capture_output=True);self.assertNotEqual(r.returncode,0,extra)
 def test_legacy_all_eight_classes_no_flag_byte_and_config_equivalence(self):
  d=Path(self.d.name);old=d/'old.c';old.write_bytes(subprocess.check_output(['git','show','e23c6bb:'+SOURCE],cwd=ROOT));exe=d/'old';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(old),'-o',str(exe)],check=True)
  for cls in ('nop','add','movi','movr','fadd','ldr','str','mov0'):
   for anchor in ('none','fsqrt'):
    for n in (0,128):
     opts=['-t',cls,'-a',anchor,'-n',str(n)];c,b=self.export(opts);f=d/'old.bin';oc=json.loads(subprocess.check_output([str(exe),*opts,'--write-asm',str(f)],text=True));self.assertEqual(c,oc);self.assertEqual(b,f.read_bytes())
if __name__=='__main__':unittest.main()
