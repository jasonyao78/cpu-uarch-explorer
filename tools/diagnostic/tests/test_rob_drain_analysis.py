"""Actual producer→consumer calibration; simulated PMU is not physical allocation proof."""
import importlib,copy,unittest
from tools.diagnostic.tests import test_rob_drain as fixture
class TestDrainAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  assert (fixture.ROOT/'tools/diagnostic/rob_drain_analysis.py').exists(),'registered drain consumer missing'
  cls.model=importlib.import_module('tools.diagnostic.rob_drain_analysis');fixture.TestDrainProducer.setUpClass();cls.actual=fixture.TestDrainProducer();cls.plan={}
  for c in cls.model.conditions('qualification'):
   a,p,g,k,rev=cls.model.identity(c);cls.plan[cls.model.plan_key(a,p,g,k,rev)]=cls.actual.plan(p,a,k,g,rev)
 @classmethod
 def tearDownClass(cls):fixture.TestDrainProducer.tearDownClass()
 def rows(self):
  rows=[]
  for c in self.model.conditions('qualification'):
   a,p,g,k,rev=self.model.identity(c);cfg,program,*schedule=self.plan[self.model.plan_key(a,p,g,k,rev)];cyc=(16 if not g else 48) if a=='none' else (k*13+16 if a=='independent' else k*26+16)
   if p=='fpcr' and a=='independent':cyc=k*26+16
   base=4096;runtime=dict(type='runtime',cpu=7,fpcr=0,code_base=base,event_ids=list(range(501,507)));ir=self.model.ITERATIONS*program['loop_instructions']+21;samples=[]
   for s in schedule:samples.append(dict(s,type='round',code_base=base,code_matches_plan=True,result_bits=[0x3ff0000000000000]*2,status_raw=0,gpr_result=0,ns=100000,enabled=10000,running=10000,counts=[cyc*self.model.ITERATIONS,ir,ir,0,0,0]))
   rows.append(self.model.audit_process([cfg,program,runtime,*samples],c,self.plan))
  return rows
 def test_actual32_plans_and_mode_qualification_do_not_overwrite(self):
  self.model.validate_plan(self.plan);rows=self.rows();d=self.model.analyze(dict(mode=self.model.MODE,phase='qualification',processes=48,rows=rows));self.assertEqual(d['status'],'FPSR_REFERENCE_QUALIFIED');self.assertTrue(d['modes']['fpsr']['qualified']);self.assertFalse(d['modes']['fpcr']['qualified']);self.assertFalse(d['physical_entries_certified'])
 def test_ir_and_original_results_not_reset_results(self):
  row=self.rows()[0];rr=[row['config'],row['program'],row['runtime'],*row['samples']];c=self.model.conditions('qualification')[0]
  for kind in ('ir','original','status','bool','order','missing'):
   bad=copy.deepcopy(rr)
   if kind=='ir':bad[3]['counts'][1]=1
   elif kind=='original':bad[3]['result_bits'][0]=0
   elif kind=='status':bad[3]['status_raw']=1
   elif kind=='bool':bad[3]['counts'][0]=True
   elif kind=='order':bad[-2:]=bad[-2:][::-1]
   else:bad.pop()
   with self.subTest(kind=kind),self.assertRaises(ValueError):self.model.audit_process(bad,c,self.plan)
 def test_scan_missing_duplicate_modes_and_supply_failure_not_rescued(self):
  with self.assertRaises(ValueError):self.model.conditions('scan')
  rows=self.rows()
  for bad in (rows[:-1],rows+[rows[-1]],rows[:2][::-1]+rows[2:]):
   with self.assertRaises(ValueError):self.model.analyze(dict(mode=self.model.MODE,phase='qualification',processes=len(bad),rows=bad))
  for row in rows:
   if row['config']['anchor']=='none' and row['config']['groups']==64:
    for i,s in enumerate(row['samples']):s['counts'][0]=(48 if i%2 else 96)*self.model.ITERATIONS
  d=self.model.analyze(dict(mode=self.model.MODE,phase='qualification',processes=48,rows=rows));self.assertEqual(d['status'],'REFERENCE_NOT_QUALIFIED')
if __name__=='__main__':unittest.main()
