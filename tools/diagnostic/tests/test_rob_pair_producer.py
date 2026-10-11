"""Real shared generator/paired schedules plus immutable legacy byte oracle."""
import json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SOURCE='docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes/rob_window_probe.c'
class PairProducer(unittest.TestCase):
 def compile(self,d,source,name):
  self.assertTrue(source.exists(),'same-address paired producer missing');exe=Path(d)/name;subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'docs/cpu-uarch-deep-analysis/rob-deep-analysis/probes'),str(source),'-o',str(exe)],check=True);return exe
 def test_actual_new_plan_schedule_and_word_level_contrasts(self):
  with tempfile.TemporaryDirectory() as d:
   exe=self.compile(d,ROOT/'probes/diagnostic/rob_dependency_pair.c','new')
   for anchor,k in [('none',16),('fsqrt',8),('fsqrt',16)]:
    for reverse in (False,True):
     args=['--plan','--anchor',anchor,'--chain',str(k),*(['--reverse'] if reverse else [])];rr=[json.loads(l) for l in subprocess.check_output([str(exe),*args],text=True).splitlines()];self.assertEqual(len(rr),37);cfg,*rest=rr;pp=rest[:4];windows=rest[4:];self.assertEqual((cfg['anchor'],cfg['chain'],cfg['windows']),(anchor,k,32));self.assertEqual([p['variant'] for p in pp],['i0','d0','i128','d128']);self.assertEqual(pp[0]['words'],pp[1]['words']);diff=[(x,y) for x,y in zip(pp[2]['words'],pp[3]['words']) if x!=y];self.assertEqual(len(diff),256);self.assertTrue(all((x^y)==((16^12)<<5) for x,y in diff));want=[(b,s,v) for b in range(8) for s,v in enumerate(['i0','d0','i128','d128'] if b%2==0 else ['d128','i128','d0','i0'])]
     if reverse:want.reverse()
     self.assertEqual([(w['block'],w['slot'],w['variant']) for w in windows],want);self.assertEqual([w['position'] for w in windows],list(range(32)))
   for args in ([],['--plan'],['--plan','--anchor','none','--chain','8'],['--plan','--anchor','miss','--chain','16']):self.assertNotEqual(subprocess.run([str(exe),*args],capture_output=True).returncode,0)
 def test_legacy_all_classes_and_dependency_config_bytes_unchanged(self):
  with tempfile.TemporaryDirectory() as d:
   before=Path(d)/'before.c';before.write_bytes(subprocess.check_output(['git','show','57f96a9:'+SOURCE],cwd=ROOT));old=self.compile(d,before,'old');new=self.compile(d,ROOT/SOURCE,'legacy');dump=Path(d)/'code'
   conditions=[]
   for cls in ('nop','add','movi','movr','fadd','ldr','str','mov0'):
    for anchor in ('none','fsqrt','miss'):
     for n in (0,128):conditions.append(['-t',cls,'-a',anchor,'-n',str(n)])
   for anchor in ('none','fsqrt'):
    for link in ('independent','dependent'):
     for n in (0,128):conditions.append(['-t','add','-a',anchor,'-n',str(n),'--anchor-link',link])
   for args in conditions:
    a=subprocess.check_output([str(old),*args,'--write-asm',str(dump)]);b=dump.read_bytes();aa=subprocess.check_output([str(new),*args,'--write-asm',str(dump)]);self.assertEqual((a,b),(aa,dump.read_bytes()),args)
if __name__=='__main__':unittest.main()
