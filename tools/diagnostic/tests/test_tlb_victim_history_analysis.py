"""Actual producer plan with explicitly synthetic external measurement windows."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
try:
    from tools.diagnostic import tlb_victim_history_analysis as model
except ImportError:model=None
ROOT=Path(__file__).resolve().parents[3]

class VictimAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=tempfile.TemporaryDirectory();exe=Path(cls.folder.name)/'producer'
        subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(ROOT/'probes/diagnostic/tlb_victim_history.cpp'),'-o',str(exe)],check=True)
        cls.plans={key:[json.loads(l) for l in subprocess.check_output([str(exe),'--plan',*args],text=True).splitlines()] for key,args in [('forward',[]),('reverse',['--reverse'])]}
    @classmethod
    def tearDownClass(cls):cls.folder.cleanup()
    def setUp(self):self.assertIsNotNone(model,'TLB victim/history consumer missing')
    def run_input(self):
        rows=[]
        for e in range(5):
            for c in self.plans['reverse' if e%2 else 'forward'][1:]:
                samples=[]
                for t in range(16):
                    for p in range(c['passes']+1):
                        victim=p==c['passes'];walk=int(victim and c['h']==1 and c['w']==9)
                        n=1 if victim else c['w']-1
                        samples.append(dict(round=t,role='victim' if victim else 'competition',pass_index=p,enabled=100,running=100,counts=[200,n,walk,n,walk,0]))
                rows.append(dict(epoch=f'epoch-{e}',**c,samples=samples))
        return dict(mode='tlb-victim-history',processes=5,rows=rows)
    def test_actual_plan_complete_raw_stream_and_rehashed_corruptions(self):
        # Geometry uses the real selector on controlled virtual coordinates;
        # backing/counts are explicitly synthetic external observations.
        src=Path(self.folder.name)/'geometry.cpp';exe=Path(self.folder.name)/'geometry'
        src.write_text('#include "tlb_victim_history_layout.h"\n#include <cstdio>\nvoid arr(const tlb_local::Addresses& a){std::printf("[");for(size_t i=0;i<a.size();++i)std::printf("%s%llu",i?",":"",(unsigned long long)a[i]);std::printf("]");}int main(){auto t=tlb_history::targets((char*)0x40000000ull,65536,100);auto f=tlb_local::fillers((char*)0x80000000ull,2048,t);std::printf("{\\\"type\\\":\\\"geometry\\\",\\\"target\\\":100,\\\"pool_base\\\":1073741824,\\\"pool_pages\\\":65536,\\\"target_pages\\\":[");arr(t[0]);std::printf(",");arr(t[1]);std::printf("],\\\"filler_pages\\\":");arr(f);std::printf("}\\n");}\n')
        subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(src),'-o',str(exe)],check=True)
        geometry=json.loads(subprocess.check_output([str(exe)],text=True))
        for e in (0,1):
            public=[c for c in self.run_input()['rows'] if c['epoch']==f'epoch-{e}']
            records=[self.plans['reverse' if e else 'forward'][0],geometry]
            for c in public:
                records.extend([dict(type='backing',cell=c['cell'],stage=stage,base_page_bytes=4096,anon_huge_kb=0) for stage in ('before','after')])
                records.extend(dict(type='round',**{k:c[k] for k in model.META if k!='rounds'},**sample) for sample in c['samples'])
            actual=model.audit_victim_history(records,bool(e),self.plans)
            self.assertEqual(actual,[{k:v for k,v in c.items() if k!='epoch'} for c in public])
            from tools.diagnostic.run_sm8650_minimal import validate_realized
            validate_realized('tlb-victim-history',['100',*(['--reverse'] if e else [])],records)
            for kind in ('geometry','backing','bool-config','missing','duplicate','order','pass','role','mux','count','metadata'):
                bad=copy.deepcopy(records)
                if kind=='geometry':bad[1]['target_pages'][0][0]+=4096
                elif kind=='backing':bad[2]['anon_huge_kb']=1
                elif kind=='bool-config':bad[0]['w_grid'][0]=True
                elif kind=='missing':bad.pop()
                elif kind=='duplicate':bad[5]=bad[4]
                elif kind=='order':bad[4:6]=bad[4:6][::-1]
                elif kind=='pass':bad[4]['pass_index']=1
                elif kind=='role':bad[4]['role']='victim'
                elif kind=='mux':bad[4]['running']=99
                elif kind=='count':bad[4]['counts'][0]=2**64
                else:bad[4]['victim']=(bad[4]['victim']+1)%12
                with self.subTest(epoch=e,kind=kind),self.assertRaises(ValueError):model.audit_victim_history(bad,bool(e),self.plans)

    def test_typed_complete_launch_identity_and_result_order(self):
        value=dict(mode='tlb-victim-history',status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,tlb_target=100,
                   protocol_path=model.PROTOCOL,build_evidence_path=model.BUILD,plan_path=model.PLAN,
                   conditions=[dict(name=f'epoch-{e}',args=['100',*(['--reverse'] if e%2 else [])]) for e in range(5)],results=[dict(name=f'epoch-{e}',exit_code=0,timed_out=False) for e in range(5)])
        self.assertTrue(hasattr(model,'validate_launch'),'complete typed launch guard missing')
        model.validate_launch(value)
        for field,bad in [('status','stopped'),('midr','0x410fd820'),('base_page_bytes',4096.0),('tlb_target',True)]:
            altered=copy.deepcopy(value);altered[field]=bad
            with self.subTest(field=field),self.assertRaises(ValueError):model.validate_launch(altered)
        for kind in ('order','missing','bool-exit','timeout'):
            altered=copy.deepcopy(value)
            if kind=='order':altered['results'][:2]=altered['results'][:2][::-1]
            elif kind=='missing':altered['results'].pop()
            elif kind=='bool-exit':altered['results'][0]['exit_code']=False
            else:altered['results'][0]['timed_out']=True
            with self.subTest(kind=kind),self.assertRaises(ValueError):model.validate_launch(altered)

    def test_complete_sampled_identity_history_response_and_no_physical_capacity(self):
        run=self.run_input();m=model.analyze(run);self.assertEqual((m['windows'],len(m['lookup_points']),len(m['victim_points']),len(m['replication'])),(40320,1920,120,12));self.assertTrue(m['all_lookup_observable']);self.assertFalse(m['physical_ways_certified']);self.assertNotIn('capacity',m);self.assertEqual(sum(p['passed'] for p in m['replication']),6)
        for kind in ('missing','order','duplicate','sample-role','typed','count','no-lookups','victim-identity','history','drift','window-residual','baseline'):
            r=copy.deepcopy(run)
            if kind=='missing':r['rows'].pop()
            elif kind=='order':r['rows'][:2]=r['rows'][:2][::-1]
            elif kind=='duplicate':r['rows'][1]=copy.deepcopy(r['rows'][0])
            elif kind=='sample-role':r['rows'][0]['samples'][0]['role']='victim'
            elif kind=='typed':r['rows'][0]['w']=True
            elif kind=='count':r['rows'][0]['samples'][0]['counts'][0]=True
            else:
                for c in r['rows']:
                    for s in c['samples']:
                        if kind=='no-lookups' and c['w']>1 and s['role']=='competition':s['counts'][3]=0
                        if c['h']==1 and s['role']=='victim':
                            if kind=='victim-identity' and c['w']==9 and c['victim']==4:s['counts'][2]=s['counts'][4]=0
                            if kind=='history' and c['w']==9 and c['history_direction']==1:s['counts'][2]=s['counts'][4]=0
                            if kind=='drift' and c['w']==9:s['counts'][2]=s['counts'][4]=int(s['round']>=8)
                            if kind=='window-residual' and c['w']==9:s['counts'][2]=s['counts'][4]=2
                            if kind=='baseline' and c['w']==1:s['counts'][2]=s['counts'][4]=1
            if kind in ('missing','order','duplicate','sample-role','typed','count'):
                with self.subTest(kind=kind),self.assertRaises(ValueError):model.analyze(r)
            else:
                out=model.analyze(r)
                if kind=='no-lookups':self.assertFalse(out['all_lookup_observable']);self.assertEqual(sum(p['passed'] for p in out['replication']),0)
                else:self.assertEqual(sum(p['passed'] for p in out['replication']),4 if kind=='victim-identity' else 3 if kind=='history' else 0)
    def test_production_plan_damage_and_driver_registration(self):
        model.validate_plan(self.plans)
        from tools.diagnostic import run_sm8650_minimal as driver
        self.assertEqual(driver.binary_name('tlb-victim-history'),'tlb_victim_history');self.assertEqual(driver.conditions('tlb-victim-history'),[(f'epoch-{e}',['100',*(['--reverse'] if e%2 else [])]) for e in range(5)])
        for kind in ('typed','missing','order','victim','history'):
            p=copy.deepcopy(self.plans)
            if kind=='typed':p['forward'][0]['reverse']=0
            elif kind=='missing':p['forward'].pop()
            elif kind=='order':p['forward'][2:4]=p['forward'][2:4][::-1]
            elif kind=='victim':p['forward'][6]['victim']=3
            else:p['forward'][6]['history_direction']=2
            with self.subTest(kind=kind),self.assertRaises(ValueError):model.validate_plan(p)
if __name__=='__main__':unittest.main()
