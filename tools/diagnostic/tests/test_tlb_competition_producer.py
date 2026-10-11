"""Real C++ plan/schedule evidence; no synthetic phone claims."""
import itertools
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'probes/diagnostic/tlb_competition.cpp'

def cells(reverse=False):
    rows=[dict(h=h,k=k,direction=d,passes=p,rounds=16) for h,k,d,p in itertools.product((1,2),(0,7,8,9,10,11),(0,1),(1,2,4,8))]
    if reverse:rows.reverse()
    return [dict(type='cell',cell=f"lookup-h{r['h']}-k{r['k']}-d{r['direction']}-p{r['passes']}",position=i,**r) for i,r in enumerate(rows)]

class CompetitionProducer(unittest.TestCase):
    def compile(self,folder,source=SOURCE):
        exe=Path(folder)/'producer'
        try:subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(source),'-o',str(exe)],check=True,capture_output=True)
        except subprocess.CalledProcessError as e:self.fail('real competition producer unavailable: '+e.stderr.decode()[:600])
        return exe
    def test_actual_forward_reverse_plan_and_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            exe=self.compile(folder)
            for rev in (False,True):
                raw=subprocess.check_output([str(exe),'--plan',*(['--reverse'] if rev else [])],text=True)
                rows=[json.loads(l) for l in raw.splitlines()]
                self.assertEqual(rows[1:],cells(rev));self.assertEqual(rows[0]['cells'],96);self.assertEqual(rows[0]['windows'],7296)
                self.assertIs(rows[0]['reverse'],rev);self.assertEqual(rows[0]['k_grid'],[0,7,8,9,10,11]);self.assertEqual(rows[0]['pass_grid'],[1,2,4,8])
            for args in ([],['200'],['--plan','--bad'],['--plan','--reverse','extra']):self.assertNotEqual(subprocess.run([str(exe),*args],capture_output=True).returncode,0)
    def test_actual_schedule_all_7296_windows(self):
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/'schedule.cpp'
            src.write_text('#include "tlb_competition_layout.h"\n#include <cstdio>\nint main(){for(const auto& c:tlb_competition::cells(false))for(const auto& s:tlb_competition::schedule(c))std::printf("%s %u %u %u\\n",c.id().c_str(),s.round,s.pass_index,s.victim?1:0);}\n')
            exe=self.compile(folder,src)
            actual=subprocess.check_output([str(exe)],text=True).splitlines()
            expected=[f"{c['cell']} {t} {p} {int(p==c['passes'])}" for c in cells() for t in range(16) for p in range(c['passes']+1)]
            self.assertEqual(actual,expected);self.assertEqual(len(actual),7296)

if __name__=='__main__':unittest.main()
