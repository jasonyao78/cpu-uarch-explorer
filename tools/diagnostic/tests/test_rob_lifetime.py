"""真实生成码的留出预测金样；外部PMU模拟仅为软件证据，不冒充E2实测。

守住 docs/design/2026-10-12-rob-lifetime-heldout.md 的固定预测、原判据不改、
只消费E2确认曲线以及前端条件/删失/覆盖硬拒绝。
"""
import copy,importlib,unittest
from tools.diagnostic import rob_zero_units_analysis as original
from tools.diagnostic.tests import test_rob_zero_units as fixture
class Lifetime(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  fixture.ZeroUnitsAnalysis.setUpClass();cls.fixture=fixture.ZeroUnitsAnalysis();original.validate_plan(cls.fixture.actual);cls.matrix=dict(mode=original.MODE,phase='scan',processes=len(original.conditions('scan')),rows=[])
  for c in original.conditions('scan'):
   rr=cls.fixture.records(c);a,p,g,k,_=original.identity(c)
   if p!='movzero-pair' and g>=256:
    for z in rr[3:]:
     if a=='independent':z['counts'][0]=(26*k if g+k>=368 else 13*k)*original.ITERATIONS
     z['counts'][5]=original.ITERATIONS//100
   cls.matrix['rows'].append(original._audit_records(rr,c))
 @classmethod
 def tearDownClass(cls):fixture.ZeroUnitsAnalysis.tearDownClass()
 def module(self):return importlib.import_module('tools.diagnostic.rob_lifetime_analysis')
 def test_frozen_predictions_with_original_icache_rejection_preserved(self):
  a=self.module().analyze(self.matrix);self.assertEqual(a['status'],'LIFETIME_PROXY_PREDICTION_REPLICATED');self.assertEqual(a['proxy_interval'],[352,368]);self.assertEqual(a['validation_epoch'],2);self.assertFalse(a['physical_entries_certified']);self.assertEqual(a['original_status'],'INCONCLUSIVE');self.assertGreater(len(a['original_icache_failures']),0)
 def test_discovery_or_epoch1_cannot_supply_confirmation(self):
  m=self.module();r=copy.deepcopy(self.matrix)
  for row in r['rows']:
   if row['condition'].startswith('e2-') or row['config']['groups']<128:continue
   for z in row['samples']:z['counts'][0]=1000*original.ITERATIONS
  a=m.analyze(r);base=m.analyze(self.matrix);self.assertEqual(a['curves'],base['curves']);self.assertEqual(a['status'],base['status'])
 def test_alternative_chain_shift_is_not_retuned(self):
  r=copy.deepcopy(self.matrix)
  for row in r['rows']:
   c=row['config']
   if row['condition'].startswith('e2-') and c['anchor']=='independent' and c['chain']==32 and c['pattern']!='movzero-pair' and c['groups']==320:
    for z in row['samples']:z['counts'][0]=832*original.ITERATIONS
  self.assertEqual(self.module().analyze(r)['status'],'PREDICTION_NOT_REPLICATED')
 def test_frontend_condition_value_flow(self):
  m=self.module()
  for ratio,expected in ((.0099,'LIFETIME_PROXY_PREDICTION_REPLICATED'),(.0101,'INCONCLUSIVE')):
   r=copy.deepcopy(self.matrix);row=next(x for x in r['rows'] if x['condition']=='e2-independent-nop-pair-g352-k16');z=row['samples'][0];z['counts'][4]=round(ratio*z['counts'][0]);self.assertEqual(m.analyze(r)['status'],expected)
 def test_missing_duplicated_reordered_or_bool_records_reject(self):
  m=self.module()
  for bad in ('missing','duplicate','order','typed'):
   r=copy.deepcopy(self.matrix)
   if bad=='missing':r['rows'].pop()
   elif bad=='duplicate':r['rows'].append(r['rows'][-1])
   elif bad=='order':r['rows'][:2]=r['rows'][:2][::-1]
   else:r['rows'][-1]['samples'][0]['counts'][0]=True
   with self.subTest(bad=bad),self.assertRaises(ValueError):m.analyze(r)
 def test_censoring_nonmonotonic_and_ambiguous_not_confirmed(self):
  m=self.module()
  for kind in ('left','right','nonmonotonic','ambiguous'):
   r=copy.deepcopy(self.matrix)
   for row in r['rows']:
    c=row['config']
    if not(row['condition'].startswith('e2-') and c['anchor']=='independent' and c['chain']==16 and c['pattern']=='nop-pair' and c['groups']>=256):continue
    rate=416 if kind=='left' or (kind=='right' and c['groups']==384) or (kind=='nonmonotonic' and c['groups'] in (336,384)) else .925*416 if kind=='ambiguous' and c['groups']==320 else 208
    for z in row['samples']:z['counts'][0]=round(rate*original.ITERATIONS)
   a=m.analyze(r);self.assertEqual(a['status'],'INCONCLUSIVE');curve=next(c for c in a['curves'] if c['pattern']=='nop-pair' and c['chain']==16);self.assertEqual(curve['status'],{'left':'left-censored','right':'right-censored','nonmonotonic':'nonmonotonic','ambiguous':'ambiguous'}[kind])
if __name__=='__main__':unittest.main()
