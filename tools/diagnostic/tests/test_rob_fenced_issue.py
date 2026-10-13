"""Actual same-PC SB swap, structural-negative calibration and production records."""
import copy,importlib,json,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
class FencedIssue(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.bin=Path(cls.tmp.name)/'fenced';subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(ROOT/'probes/common'),str(ROOT/'probes/diagnostic/rob_fenced_issue_marker.c'),'-o',str(cls.bin)],check=True,capture_output=True);cls.plans={str(k):[json.loads(l) for l in subprocess.check_output([str(cls.bin),'--plan','--chain',str(k)],text=True).splitlines()] for k in (16,32)}
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_actual_fixed_branch_pc_two_word_fence_swap(self):
  for key,p in self.plans.items():
   k=int(key);self.assertEqual((len(p),p[0]['windows']),(261,256));pp={(z['fence'],z['marker']):z['words'] for z in p[1:5]}
   for marker in ('nop','taps'):
    a,b=pp['pre',marker],pp['post',marker];self.assertEqual(len(a),k+29);self.assertEqual(a[k+4],0xb500026c);self.assertEqual(a[k+23],0xd50330ff);self.assertEqual([(i,x,y) for i,(x,y) in enumerate(zip(a,b)) if x!=y],[(k+5,0xd50330ff,0xd503201f),(k+22,0xd503201f,0xd50330ff)]);self.assertEqual(sorted(a),sorted(b))
   for ctl in ('architect','speculate'):
    for fence in ('pre','post'):
     for marker in ('nop','taps'):
      s=[z for z in p[5:] if (z['control'],z['fence'],z['marker'])==(ctl,fence,marker)];self.assertEqual(len(s),32);self.assertEqual(sorted(z['position'] for z in s),[j for j in range(8) for _ in range(4)])
 def model(self):return importlib.import_module('tools.diagnostic.rob_fenced_issue_analysis')
 def rows(self):
  m=self.model();rows=[]
  for c in m.conditions('qualification'):
   k=int(c['args'][2]);p=self.plans[str(k)];runtime=dict(type='runtime',cpu=7,fpcr=0,hwcap_sb=True,code_base=1<<32,near_base=2<<32,far_base=3<<32,output_base=4<<32,pagemap_before=[(1<<63)|x for x in (10,20,30,40)],event_ids=list(range(100,106)));samples=[]
   for z in p[5:]:
    tap=z['marker']=='taps';active=tap and (z['control']=='architect' or z['fence']=='post');arch=m.MARKER if tap and z['control']=='architect' else 0;samples.append(dict(z,type='round',result_bits=z['test_bits'],status_raw=0,near_architectural=arch,far_architectural_words=[arch]*8,code_base=1<<32,code_matches_plan=True,enabled=1000,running=1000,counts=[500,k+100,20+8*active,20+8*active,int(z['control']=='speculate'),4]))
   rows.append(m.audit_process([*p[:5],runtime,*samples,dict(type='final',pagemap_after=runtime['pagemap_before'][:],fds_closed=True)],c,self.plans))
  return rows
 def matrix(self):return dict(mode=self.model().MODE,phase='qualification',processes=6,rows=self.rows())
 def test_complete_structural_negative_positive_no_capacity_claim(self):
  m=self.model();m.validate_plan(self.plans);a=m.analyze(self.matrix());self.assertEqual((a['status'],a['windows']),('FENCED_ISSUE_MARKER_QUALIFIED',1536));self.assertEqual(a['processes'][0]['thresholds'],dict(near=4,far=4));self.assertFalse(a['physical_capacity_certified'])
 def test_pre_leak_post_absence_bad_positive_all_refuse(self):
  m=self.model()
  for kind in ('pre-leak','post-absence','far-absence','positive'):
   x=self.matrix()
   for z in x['rows'][0]['samples']:
    if z['marker']!='taps':continue
    if kind=='pre-leak' and z['control']=='speculate' and z['fence']=='pre':z['counts'][2]+=8
    elif kind=='post-absence' and z['control']=='speculate' and z['fence']=='post':z['counts'][2]-=8
    elif kind=='far-absence' and z['control']=='speculate' and z['fence']=='post':z['counts'][3]-=8
    elif kind=='positive' and z['control']=='architect':z['counts'][3]-=8
   with self.subTest(kind=kind):self.assertEqual(m.analyze(x)['status'],'FENCED_ISSUE_MARKER_NOT_QUALIFIED')
 def test_typed_coverage_fence_architecture_and_result_reject(self):
  m=self.model();row=self.rows()[0];rr=[row['config'],*row['programs'],row['runtime'],*row['samples'],row['final']]
  for kind in ('typed','missing','fence','arch','word','PFN'):
   bad=copy.deepcopy(rr)
   if kind=='typed':bad[7]['counts'][2]=True
   elif kind=='missing':bad.pop(6)
   elif kind=='fence':bad[7]['fence']='post'
   elif kind=='arch':bad[7]['far_architectural_words'][7]^=1
   elif kind=='word':bad[2]['words'][21]^=1
   elif kind=='PFN':bad[-1]['pagemap_after'][0]+=1
   with self.subTest(kind=kind),self.assertRaises(ValueError):m.audit_process(bad,m.conditions('qualification')[0],self.plans)
  with self.assertRaises(ValueError):m.conditions('scan')
