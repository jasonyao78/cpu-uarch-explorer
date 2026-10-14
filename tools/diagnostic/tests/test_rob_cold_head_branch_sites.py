"""守住真实PC干预而非只改requested字段；锚点 branch-sites v1.0。"""
import importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class BranchSites(unittest.TestCase):
 def test_actual_native_site_offsets_and_bounds(self):
  src=ROOT/'probes/diagnostic/rob_cold_head_branch_sites.c';self.assertTrue(src.exists(),'branch-sites producer missing')
  with tempfile.TemporaryDirectory() as td:
   b=Path(td)/'p';subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-std=c11','-I'+str(ROOT/'probes/common'),str(src),'-o',str(b)],check=True)
   for heads in (1,2):
    for layout in ('fixed','trial-role','packet'):
     args=['--plan','--heads',str(heads),'--palette','issue','--head-offset','1024','--branch-layout',layout,'--indices','32,3,4,5,6,7'];rr=[json.loads(l) for l in subprocess.check_output([str(b),*args]).splitlines()]
     from tools.diagnostic import rob_cold_head_branch_sites_analysis as model
     self.assertEqual(rr,model.expected(heads,'issue',1024,layout));self.assertEqual(rr[0]['branch_layout'],layout);sch=rr[5:];self.assertEqual(len(sch),512)
     distinct={z['code_offset'] for z in sch};self.assertEqual(len(distinct),{'fixed':1,'trial-role':256,'packet':512}[layout])
     self.assertLess(max(distinct)+max(p['code_bytes'] for p in rr[1:5]),4096)
     for z in sch:self.assertEqual(z['branch_offset'],z['code_offset']+4*(33+heads))
     pairs={(z['trial'],z['control'],z['fence'],z['marker'],z['state']):z['code_offset'] for z in sch}
     for z in sch:
      other=pairs[z['trial'],z['control'],z['fence'],z['marker'],'hot' if z['state']=='cold' else 'cold']
      self.assertEqual(z['code_offset']==other,layout!='packet')
 def test_consumer_controller_and_plans_agree(self):
  try:m=importlib.import_module('tools.diagnostic.rob_cold_head_branch_sites_analysis');d=importlib.import_module('tools.diagnostic.run_sm8650_rob_cold_head_branch_sites')
  except ModuleNotFoundError:self.fail('branch-sites consumer/controller missing')
  self.assertEqual(m.PROTOCOL,d.PROTOCOL);self.assertTrue((ROOT/d.PROTOCOL).exists());self.assertEqual(len(m.conditions()),12)
  with self.assertRaises(ValueError):m.analyze([])
