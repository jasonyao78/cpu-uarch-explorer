"""Real resident producer plans; external PMU fixtures are software evidence only."""
import json,subprocess,tempfile,unittest,struct
from pathlib import Path
from tools.diagnostic.rob_dependency_analysis import expected_code
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'probes/diagnostic/rob_resident_control.c'
SPECS=[('none','independent',0),('none','independent',128),('none','dependent',128),('fsqrt','independent',128),('fsqrt','dependent',128)]
class ResidentProducer(unittest.TestCase):
 def test_real_program_and_all_schedules(self):
  self.assertTrue(SOURCE.exists(),'resident control producer missing')
  with tempfile.TemporaryDirectory() as d:
   exe=Path(d)/'resident';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),str(SOURCE),'-o',str(exe)],check=True)
   for a,link,n in SPECS:
    for rev in (False,True):
     args=['--plan','--anchor',a,'--link',link,'--n',str(n),*(['--reverse'] if rev else [])]
     rr=[json.loads(l) for l in subprocess.check_output([str(exe),*args],text=True).splitlines()];self.assertEqual(len(rr),18);cfg,p,*ss=rr
     self.assertEqual((cfg['probe'],cfg['anchor'],cfg['link'],cfg['n'],cfg['windows']),('rob-resident-control',a,link,n,16))
     code=expected_code({'args':['--anchor-link',link,'-a',a,'--chain','16','-n',str(n)]});self.assertEqual(struct.pack('<'+'I'*len(p['words']),*p['words']),code)
     want=[(b,s,v) for b in range(8) for s,v in enumerate(['resident','reinstall'] if b%2==0 else ['reinstall','resident'])]
     if rev:want.reverse()
     self.assertEqual([(w['block'],w['slot'],w['preparation']) for w in ss],want)
     g=1
     for pos,s in enumerate(ss):
      g+=s['preparation']=='reinstall';self.assertEqual((s['position'],s['installation_generation']),(pos,g))
   for args in ([],['--plan'],['--plan','--anchor','none','--link','dependent','--n','0'],['--plan','--anchor','fsqrt','--link','independent','--n','0']):self.assertNotEqual(subprocess.run([str(exe),*args],capture_output=True).returncode,0)
if __name__=='__main__':unittest.main()
