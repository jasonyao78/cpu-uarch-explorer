"""Actual C flags with synthetic kernel mmap metadata; no target evidence."""
import copy,json,subprocess,unittest
from tools.diagnostic.tests import test_pmu_user_metadata as producer
from tools.diagnostic import pmu_user_metadata_analysis as m
class MetadataAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):producer.UserMetadata.setUpClass();cls.plan={str(f):json.loads(subprocess.check_output([str(producer.UserMetadata.bin),'--plan','--config1',str(f)],text=True)) for f in (2,3)}
 @classmethod
 def tearDownClass(cls):producer.UserMetadata.tearDownClass()
 def records(self,policy=0):return [self.plan['2'],dict(type='policy',perf_user_access=policy,read_only=True),dict(type='metadata',cpu=7,events=[dict(event=e,id=100+i,index=i+1,pmc_width=32,cap_user_rdpmc=bool(policy),offset=0,sequence_before=2,sequence_after=2) for i,e in enumerate(m.EVENTS)]),dict(type='final',fds_closed=True,global_policy_mutation=False,counter_register_reads=0,counter_read_qualified=False)]
 def test_actual_plan_disabled_and_enabled_metadata_never_qualifies_reads(self):
  for policy,status in ((0,'ACCESS_DISABLED'),(1,'METADATA_INTAKE_COMPLETE')):
   a=m.audit_process(self.records(policy),m.conditions()[0],self.plan);self.assertEqual(a['status'],status);self.assertFalse(a['counter_read_qualified']);self.assertFalse(a['physical_capacity_certified'])
 def test_policy_cap_id_identity_and_register_count_types_reject(self):
  for kind in ('policy','cap','ids','event','index','width','read','mutation','fd','missing'):
   v=copy.deepcopy(self.records())
   if kind=='policy':v[1]['perf_user_access']=False
   elif kind=='cap':v[2]['events'][0]['cap_user_rdpmc']=0
   elif kind=='ids':v[2]['events'][1]['id']=v[2]['events'][0]['id']
   elif kind=='event':v[2]['events'][0]['event']=6
   elif kind=='index':v[2]['events'][0]['index']=33
   elif kind=='width':v[2]['events'][0]['pmc_width']=False
   elif kind=='read':v[-1]['counter_register_reads']=1
   elif kind=='mutation':v[-1]['global_policy_mutation']=True
   elif kind=='fd':v[-1]['fds_closed']=False
   elif kind=='missing':v.pop(2)
   with self.subTest(kind=kind),self.assertRaises(ValueError):m.audit_process(v,m.conditions()[0],self.plan)
 def test_actual_host_first_failure_and_kernel_policy_denial_named(self):
  p=subprocess.run([str(producer.UserMetadata.bin),'--run','--config1','2'],text=True,capture_output=True);v=[json.loads(l) for l in p.stdout.splitlines()];self.assertEqual(m.audit_process(v,m.conditions()[0],self.plan)['status'],'TECHNICAL_FAILURE')
  v=[self.plan['2'],dict(type='policy',perf_user_access=0,read_only=True),dict(type='failure',metrics={},failure=dict(reason='perf-open-user-config',errno=13),fds_closed=True,global_policy_mutation=False,counter_register_reads=0)];a=m.audit_process(v,m.conditions()[0],self.plan);self.assertEqual((a['status'],a['policy']),('CAPABILITY_UNAVAILABLE',0));self.assertFalse(a['counter_read_qualified'])
