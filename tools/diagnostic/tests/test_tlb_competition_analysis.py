"""Actual producer plan with explicitly synthetic external measurement windows."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
try:
    from tools.diagnostic import tlb_competition_analysis as model
except ImportError:model=None
ROOT=Path(__file__).resolve().parents[3]

class CompetitionAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder=tempfile.TemporaryDirectory();exe=Path(cls.folder.name)/'producer'
        subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(ROOT/'probes/diagnostic/tlb_competition.cpp'),'-o',str(exe)],check=True)
        cls.plans={key:[json.loads(l) for l in subprocess.check_output([str(exe),'--plan',*args],text=True).splitlines()] for key,args in [('forward',[]),('reverse',['--reverse'])]}
    @classmethod
    def tearDownClass(cls):cls.folder.cleanup()
    def setUp(self):self.assertIsNotNone(model,'TLB competition consumer missing')
    def run_input(self):
        rows=[]
        for e in range(5):
            for c in self.plans['reverse' if e%2 else 'forward'][1:]:
                samples=[]
                for t in range(16):
                    for p in range(c['passes']+1):
                        victim=p==c['passes'];walk=int(victim and c['h']==1 and c['k']>=9 and c['passes']>=4)
                        n=1 if victim else c['k']
                        samples.append(dict(round=t,role='victim' if victim else 'competition',pass_index=p,enabled=100,running=100,counts=[200,n,walk,n,walk,0]))
                rows.append(dict(epoch=f'epoch-{e}',**c,samples=samples))
        return dict(mode='tlb-competition',processes=5,rows=rows)
    def test_actual_plan_complete_raw_stream_and_rehashed_corruptions(self):
        # Geometry uses the real selector on controlled virtual coordinates;
        # backing/counts are explicitly synthetic external observations.
        src=Path(self.folder.name)/'geometry.cpp';exe=Path(self.folder.name)/'geometry'
        src.write_text('#include "tlb_competition_layout.h"\n#include <cstdio>\nvoid arr(const tlb_local::Addresses& a){std::printf("[");for(size_t i=0;i<a.size();++i)std::printf("%s%llu",i?",":"",(unsigned long long)a[i]);std::printf("]");}int main(){auto t=tlb_history::targets((char*)0x40000000ull,65536,100);auto f=tlb_local::fillers((char*)0x80000000ull,2048,t);std::printf("{\\\"type\\\":\\\"geometry\\\",\\\"target\\\":100,\\\"pool_base\\\":1073741824,\\\"pool_pages\\\":65536,\\\"target_pages\\\":[");arr(t[0]);std::printf(",");arr(t[1]);std::printf("],\\\"filler_pages\\\":");arr(f);std::printf("}\\n");}\n')
        subprocess.run(['clang++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'probes/common'),'-I',str(ROOT/'probes/diagnostic'),str(src),'-o',str(exe)],check=True)
        geometry=json.loads(subprocess.check_output([str(exe)],text=True))
        for e in (0,1):
            public=[c for c in self.run_input()['rows'] if c['epoch']==f'epoch-{e}']
            records=[self.plans['reverse' if e else 'forward'][0],geometry]
            for c in public:
                records.extend([dict(type='backing',cell=c['cell'],stage=stage,base_page_bytes=4096,anon_huge_kb=0) for stage in ('before','after')])
                records.extend(dict(type='round',**{k:c[k] for k in model.META if k!='rounds'},**sample) for sample in c['samples'])
            actual=model.audit_competition(records,bool(e),self.plans)
            self.assertEqual(actual,[{k:v for k,v in c.items() if k!='epoch'} for c in public])
            from tools.diagnostic.run_sm8650_minimal import validate_realized
            validate_realized('tlb-competition',['100',*(['--reverse'] if e else [])],records)
            for kind in ('geometry','backing','bool-config','missing','duplicate','order','pass','role','mux','count','metadata'):
                bad=copy.deepcopy(records)
                if kind=='geometry':bad[1]['target_pages'][0][0]+=4096
                elif kind=='backing':bad[2]['anon_huge_kb']=1
                elif kind=='bool-config':bad[0]['k_grid'][0]=False
                elif kind=='missing':bad.pop()
                elif kind=='duplicate':bad[5]=bad[4]
                elif kind=='order':bad[4:6]=bad[4:6][::-1]
                elif kind=='pass':bad[4]['pass_index']=1
                elif kind=='role':bad[4]['role']='victim'
                elif kind=='mux':bad[4]['running']=99
                elif kind=='count':bad[4]['counts'][0]=2**64
                else:bad[4]['k']=8
                with self.subTest(epoch=e,kind=kind),self.assertRaises(ValueError):model.audit_competition(bad,bool(e),self.plans)

    def test_typed_complete_launch_identity_and_result_order(self):
        value=dict(mode='tlb-competition',status='complete',target='redmi-k70pro-01',midr='0x410fd821',base_page_bytes=4096,tlb_target=100,
                   protocol_path=model.PROTOCOL,build_evidence_path='docs/reviews/evidence/2026-10-10-tlb-competition/build.json',plan_path='docs/reviews/evidence/2026-10-10-tlb-competition/plan.json',
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

    def test_real_plan_typed_full_order_and_budget(self):
        run=self.run_input();model.audit_cells(run);result=model.analyze(run)
        self.assertEqual(result['windows'],36480);self.assertEqual(len(result['lookup_points']),1500)
        self.assertTrue(result['all_lookup_observable']);self.assertFalse(result['physical_ways_certified'])
        self.assertNotIn('capacity',result);self.assertEqual(len(result['victim_points']),240)
        from tools.diagnostic import run_sm8650_minimal as driver
        self.assertEqual(driver.conditions('tlb-competition'),[(f'epoch-{e}',['100',*(['--reverse'] if e%2 else [])]) for e in range(5)])
        self.assertEqual(driver.binary_name('tlb-competition'),'tlb_competition')
    def test_registered_plan_damage_and_wrong_typed_config_reject(self):
        model.validate_plan(self.plans)
        for kind in ('bool','missing','order','duplicate','metadata'):
            plan=copy.deepcopy(self.plans)
            if kind=='bool':plan['forward'][0]['reverse']=0
            elif kind=='missing':plan['forward'].pop()
            elif kind=='order':plan['forward'][2:4]=plan['forward'][2:4][::-1]
            elif kind=='duplicate':plan['forward'][3]=plan['forward'][2]
            else:plan['forward'][2]['k']=6
            with self.subTest(kind=kind),self.assertRaises(ValueError):model.validate_plan(plan)
    def test_missing_duplicate_order_role_pass_mux_and_counts_reject(self):
        for kind in ('missing','duplicate','order','role','pass','mux','bool','count','counts-length'):
            run=self.run_input();samples=run['rows'][0]['samples']
            if kind=='missing':run['rows'].pop()
            elif kind=='duplicate':run['rows'][1]=run['rows'][0]
            elif kind=='order':run['rows'][:2]=run['rows'][:2][::-1]
            elif kind=='role':samples[0]['role']='victim'
            elif kind=='pass':samples[0]['pass_index']=1
            elif kind=='mux':samples[0]['running']=99
            elif kind=='bool':samples[0]['round']=False
            elif kind=='count':samples[0]['counts'][4]=True
            else:samples[0]['counts'].pop()
            with self.subTest(kind=kind),self.assertRaises(ValueError):model.analyze(run)
    def test_lookup_gate_uses_matched_k0_per_pass_and_h(self):
        run=self.run_input()
        for c in run['rows']:
            for s in c['samples']:
                if s['role']=='competition':s['counts'][1]+=3;s['counts'][3]+=3
        self.assertTrue(model.analyze(run)['all_lookup_observable'])
        for c in run['rows']:
            if c['epoch']=='epoch-0' and c['h']==1 and c['k']==11 and c['direction']==0 and c['passes']==8:
                for s in c['samples']:
                    if s['role']=='competition' and s['pass_index']==7:s['counts'][3]=3
        result=model.analyze(run);bad=[p for p in result['lookup_points'] if not p['observable']]
        self.assertEqual(len(bad),1);self.assertEqual(bad[0]['pass_index'],7)
    def test_repeated_victim_response_needs_both_orders_and_four_epochs(self):
        run=self.run_input();result=model.analyze(run)
        selected=[p for p in result['replication'] if p['k']==9 and p['passes']==4][0]
        self.assertTrue(selected['passed']);self.assertEqual(selected['epochs'],5)
        for c in run['rows']:
            if c['epoch'] in ('epoch-0','epoch-1') and c['direction']==1:
                for s in c['samples']:
                    if s['role']=='victim':s['counts'][4]=0
        selected=[p for p in model.analyze(run)['replication'] if p['k']==9 and p['passes']==4][0]
        self.assertFalse(selected['passed']);self.assertEqual(selected['epochs'],3)
    def test_count_over_one_drift_and_baseline_not_rescued(self):
        for kind in ('count','drift','baseline'):
            run=self.run_input()
            for c in run['rows']:
                if c['epoch']=='epoch-0' and c['h']==1 and c['direction']==0 and c['passes']==4 and c['k']==(0 if kind=='baseline' else 9):
                    for s in c['samples']:
                        if s['role']=='victim':s['counts'][4]=2 if kind=='count' else int(s['round']<8) if kind=='drift' else 1
            point=[p for p in model.analyze(run)['victim_points'] if p['epoch']=='epoch-0' and p['direction']==0 and p['passes']==4 and p['k']==9][0]
            self.assertFalse(point['response_observed']);self.assertTrue(point['issues'])

if __name__=='__main__':unittest.main()
