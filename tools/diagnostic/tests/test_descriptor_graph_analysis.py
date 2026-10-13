"""Actual producer plans/VM -> declared cycle/typed parent layout; synthetic memory only."""
import copy,importlib,json,subprocess,unittest
from tools.diagnostic.tests import test_descriptor_graph as producer
from tools.diagnostic.tests import test_translation_install as old
from tools.diagnostic.tests import test_translation_self as vm
class DescriptorGraphAnalysis(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.path=producer.ROOT/'tools/diagnostic/descriptor_graph_analysis.py'
  if cls.path.exists():
   cls.m=importlib.import_module('tools.diagnostic.descriptor_graph_analysis');producer.DescriptorGraphProducer.setUpClass();cls.actual=producer.DescriptorGraphProducer();cls.plan=cls.actual.plan()
 @classmethod
 def tearDownClass(cls):
  if hasattr(cls,'actual'):producer.DescriptorGraphProducer.tearDownClass()
 def test_registered_consumer_exists(self):self.assertTrue(self.path.exists(),'descriptor graph consumer missing')
 def records(self):
  self.assertTrue(self.path.exists(),'descriptor graph consumer missing');n=32;bases=[1<<32,(1<<32)+(1<<30)];canon=[(1<<63)|(0xaaa+j) for j in range(n)];records=[self.plan,dict(type='mapping',owner_pid=12345,bases=bases,canonical_base=3<<32,nodes=32),dict(type='canonical-before',entries=canon)];plans=[]
  for shape in range(2):
   for j in range(n):
    va=bases[shape]+j*[8192,2105344][shape];p=json.loads(subprocess.check_output([str(self.actual.binary),'--bpf-plan','12345',str(va),'7'],text=True));plans.append(p);parent=0x600+0x50*shape;leaf=0x700 if not shape else 0x800+j;pm=old.BIAS+parent*4096+8*((va>>21)&511);pt=old.BIAS+leaf*4096+8*((va>>12)&511);root=vm.PGD+8*((va>>30)&511)
    memory={old.VMF+48:(8,pm),old.VMF+88:(8,pt),pm:(8,leaf*4096+3),root:(8,parent*4096+3),pt:(8,(0xaaa+j)*4096+3)};args=dict(context_fields={0:old.VMF,16:va},additional_memory=memory,allowed_reads=[(old.VMF+48,8),(old.VMF+88,8),(pm,8),(vm.TASK+1440,8),(vm.MM+56,8),(root,8),(pt,8)],output_words=16);entry,_=vm.interpret(p['entry_instructions'],**args);out,_=vm.interpret(p['return_instructions'],prior=entry,**args);pair=[canon[j],canon[j^1]]
    records.append(dict(type='install-read',shape=shape,node=j,node_word=self.plan['next'][j],cpu=7,page_bytes=4096,kprobe_type=7,program=p,initial=[0]*16,negative=[0]*16,positive=out,alias_before=[0]*2,alias_after=pair,canonical_before=pair,canonical_after=pair,fds_closed=True))
   records.append(dict(type='graph-final',shape=shape,loads=512,head_returned=True,entries=canon,words=self.plan['next']))
  records.append(dict(type='canonical-after',entries=canon));return records,plans
 def test_complete_real_cycle_parent_activation(self):
  self.assertTrue(self.path.exists(),'descriptor graph consumer missing');rr,pp=self.records();r=self.m.audit_process(rr,pp,self.plan);self.assertEqual(r['status'],'DESCRIPTOR_GRAPH_BOUND');self.assertEqual(r['captures'],64);self.assertEqual([z['leaf_table_pages'] for z in r['shapes']],[1,32]);self.assertEqual([z['leaf_entry_lines'] for z in r['shapes']],[8,32]);self.assertFalse(r['physical_capacity_certified'])
 def test_missing_duplicated_order_pfn_words_and_parent_layout_refuse(self):
  self.assertTrue(self.path.exists(),'descriptor graph consumer missing');rr,pp=self.records()
  for kind in ('missing','duplicate','order','pfn','word','typed','head','parent'):
   bad=copy.deepcopy(rr)
   if kind=='missing':bad.pop(4)
   if kind=='duplicate':bad.insert(4,bad[3])
   if kind=='order':bad[3:5]=bad[3:5][::-1]
   if kind=='pfn':bad[-1]['entries'][0]+=1
   if kind=='word':bad[3]['node_word']+=1
   if kind=='typed':bad[3]['node']=False
   if kind=='head':bad[35]['head_returned']=False
   if kind=='parent':bad[3]['positive'][8]+=4096
   with self.subTest(kind=kind),self.assertRaises(ValueError):self.m.audit_process(bad,pp,self.plan)
 def test_named_first_no_excitation_and_denial(self):
  self.assertTrue(self.path.exists(),'descriptor graph consumer missing');rr,pp=self.records();short=copy.deepcopy(rr[:4]);short[-1]['positive']=[0]*16;short.append(dict(type='stop',reason='not-excited',captures=1));r=self.m.audit_process(short,pp[:1],self.plan);self.assertEqual((r['status'],r['captures']),('NOT_EXCITED',1))
  short=[*rr[:3],dict(type='failure',metrics={},failure=dict(reason='bpf-program-load',errno=13))];self.assertEqual(self.m.audit_process(short,[],self.plan)['status'],'CAPABILITY_UNAVAILABLE')
if __name__=='__main__':unittest.main()
